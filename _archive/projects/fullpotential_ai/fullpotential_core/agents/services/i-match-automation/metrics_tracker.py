"""
I MATCH Metrics Tracker
Real-time tracking of Phase 1 launch progress
"""

import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import os


class LaunchMetrics(BaseModel):
    """I MATCH launch metrics"""
    # Current counts
    total_providers: int = 0
    total_customers: int = 0
    total_matches: int = 0

    # Today's activity
    providers_today: int = 0
    customers_today: int = 0
    matches_today: int = 0

    # Week 1 goals (Phase 1, Month 1)
    goal_providers: int = 20  # Week 1 target
    goal_customers: int = 10  # Week 1 target
    goal_matches: int = 10   # Month 1 target

    # Progress percentages
    providers_progress: float = 0.0
    customers_progress: float = 0.0
    matches_progress: float = 0.0

    # Status
    on_track: bool = False
    days_into_week: int = 0
    expected_providers: float = 0.0
    expected_customers: float = 0.0

    # Revenue estimate
    estimated_revenue: float = 0.0  # Based on $500-$1000 per match


class MatchDetail(BaseModel):
    """Individual match details"""
    match_id: int
    customer_name: str
    provider_name: str
    match_score: int
    created_at: str
    status: str


class MetricsTracker:
    """Track I MATCH launch metrics from database"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "I_MATCH_DB_PATH",
            "/Users/jamessunheart/Development/agents/services/i-match/i_match.db"
        )

    def _get_connection(self):
        """Get database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except Exception as e:
            raise Exception(f"Cannot connect to I MATCH database: {e}")

    def get_launch_metrics(self) -> LaunchMetrics:
        """Get comprehensive launch metrics"""

        metrics = LaunchMetrics()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Total providers
            cursor.execute("SELECT COUNT(*) FROM providers")
            metrics.total_providers = cursor.fetchone()[0]

            # Total customers
            cursor.execute("SELECT COUNT(*) FROM customers")
            metrics.total_customers = cursor.fetchone()[0]

            # Total matches
            cursor.execute("SELECT COUNT(*) FROM matches")
            metrics.total_matches = cursor.fetchone()[0]

            # Today's counts
            today = datetime.now().strftime("%Y-%m-%d")

            cursor.execute(
                "SELECT COUNT(*) FROM providers WHERE created_at >= ?",
                (today,)
            )
            metrics.providers_today = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM customers WHERE created_at >= ?",
                (today,)
            )
            metrics.customers_today = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM matches WHERE created_at >= ?",
                (today,)
            )
            metrics.matches_today = cursor.fetchone()[0]

            conn.close()

        except Exception as e:
            # If database doesn't exist or has issues, return zeros
            pass

        # Calculate progress
        metrics.providers_progress = min(
            (metrics.total_providers / metrics.goal_providers * 100) if metrics.goal_providers > 0 else 0,
            100
        )
        metrics.customers_progress = min(
            (metrics.total_customers / metrics.goal_customers * 100) if metrics.goal_customers > 0 else 0,
            100
        )
        metrics.matches_progress = min(
            (metrics.total_matches / metrics.goal_matches * 100) if metrics.goal_matches > 0 else 0,
            100
        )

        # Calculate days into week (assuming launch started today if no data)
        # In production, this would track from actual launch date
        metrics.days_into_week = 1

        # Expected progress (linear projection)
        metrics.expected_providers = (metrics.goal_providers / 7) * metrics.days_into_week
        metrics.expected_customers = (metrics.goal_customers / 7) * metrics.days_into_week

        # On track if actual >= expected
        metrics.on_track = (
            metrics.total_providers >= metrics.expected_providers and
            metrics.total_customers >= metrics.expected_customers
        )

        # Revenue estimate ($500-$1000 per match, use $750 average)
        metrics.estimated_revenue = metrics.total_matches * 750

        return metrics

    def get_recent_matches(self, limit: int = 10) -> List[MatchDetail]:
        """Get recent matches"""

        matches = []

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    m.id,
                    c.name as customer_name,
                    p.name as provider_name,
                    m.match_score,
                    m.created_at,
                    COALESCE(m.status, 'pending') as status
                FROM matches m
                JOIN customers c ON m.customer_id = c.id
                JOIN providers p ON m.provider_id = p.id
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (limit,))

            for row in cursor.fetchall():
                matches.append(MatchDetail(
                    match_id=row[0],
                    customer_name=row[1],
                    provider_name=row[2],
                    match_score=row[3],
                    created_at=row[4],
                    status=row[5]
                ))

            conn.close()

        except Exception as e:
            # Return empty list if database issues
            pass

        return matches

    def get_daily_breakdown(self, days: int = 7) -> Dict[str, Dict]:
        """Get daily breakdown for last N days"""

        breakdown = {}

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

                cursor.execute(
                    "SELECT COUNT(*) FROM providers WHERE DATE(created_at) = ?",
                    (date,)
                )
                providers = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM customers WHERE DATE(created_at) = ?",
                    (date,)
                )
                customers = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM matches WHERE DATE(created_at) = ?",
                    (date,)
                )
                matches = cursor.fetchone()[0]

                breakdown[date] = {
                    "providers": providers,
                    "customers": customers,
                    "matches": matches
                }

            conn.close()

        except Exception as e:
            # Return empty breakdown if issues
            pass

        return breakdown


# CLI for testing
if __name__ == "__main__":
    print("📊 I MATCH Metrics Tracker")
    print("=" * 50)

    tracker = MetricsTracker()

    try:
        metrics = tracker.get_launch_metrics()

        print(f"\n🎯 WEEK 1 PROGRESS")
        print(f"Providers: {metrics.total_providers}/{metrics.goal_providers} ({metrics.providers_progress:.1f}%)")
        print(f"Customers: {metrics.total_customers}/{metrics.goal_customers} ({metrics.customers_progress:.1f}%)")
        print(f"Matches: {metrics.total_matches}/{metrics.goal_matches} ({metrics.matches_progress:.1f}%)")

        print(f"\n📈 TODAY'S ACTIVITY")
        print(f"Providers added: {metrics.providers_today}")
        print(f"Customers added: {metrics.customers_today}")
        print(f"Matches created: {metrics.matches_today}")

        print(f"\n🎯 ON TRACK: {'✅ YES' if metrics.on_track else '❌ NO'}")
        print(f"Expected providers by now: {metrics.expected_providers:.1f}")
        print(f"Expected customers by now: {metrics.expected_customers:.1f}")

        print(f"\n💰 ESTIMATED REVENUE")
        print(f"${metrics.estimated_revenue:,.0f} (based on {metrics.total_matches} matches)")

        print(f"\n🔄 RECENT MATCHES")
        matches = tracker.get_recent_matches(5)
        if matches:
            for m in matches:
                print(f"  {m.customer_name} ↔ {m.provider_name} (score: {m.match_score}/10)")
        else:
            print("  No matches yet")

    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        print("Database may not exist yet. This is normal before first launch.")

    print("\n" + "=" * 50)

"""
Referral Tracking System for I MATCH Contributors
Tracks who refers whom and calculates commissions
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, List
import json

class ReferralTracker:
    def __init__(self, db_path: str = "imatch.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create referral tracking tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Referral codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referral_code TEXT UNIQUE NOT NULL,
                contributor_email TEXT,
                contributor_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tier INTEGER DEFAULT 1,
                total_signups INTEGER DEFAULT 0,
                total_revenue_generated REAL DEFAULT 0.0,
                total_commission_earned REAL DEFAULT 0.0
            )
        ''')

        # Referral signups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referral_code TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revenue_generated REAL DEFAULT 0.0,
                commission_paid REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (referral_code) REFERENCES referral_codes(referral_code)
            )
        ''')

        # Commission payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commission_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referral_code TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_method TEXT,
                payment_id TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (referral_code) REFERENCES referral_codes(referral_code)
            )
        ''')

        conn.commit()
        conn.close()

    def create_referral_code(self, referral_code: str, email: Optional[str] = None,
                            name: Optional[str] = None, tier: int = 1) -> Dict:
        """Create a new referral code for a contributor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO referral_codes (referral_code, contributor_email, contributor_name, tier)
                VALUES (?, ?, ?, ?)
            ''', (referral_code, email, name, tier))
            conn.commit()

            return {
                "success": True,
                "referral_code": referral_code,
                "tracking_url": f"http://198.54.123.234:8401?ref={referral_code}",
                "tier": tier,
                "commission_rate": self.get_commission_rate(tier)
            }
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "error": "Referral code already exists"
            }
        finally:
            conn.close()

    def get_commission_rate(self, tier: int) -> float:
        """Get commission rate based on tier"""
        rates = {
            1: 0.10,  # 10% for Tier 1 (Content Creators)
            2: 0.20,  # 20% for Tier 2 (Direct Outreach)
            3: 0.05   # 5% for Tier 3 (Ambassador - second tier)
        }
        return rates.get(tier, 0.10)

    def track_signup(self, referral_code: str, customer_email: str) -> Dict:
        """Track a signup from a referral"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if referral code exists
            cursor.execute('SELECT tier FROM referral_codes WHERE referral_code = ?', (referral_code,))
            result = cursor.fetchone()

            if not result:
                return {"success": False, "error": "Invalid referral code"}

            tier = result[0]

            # Record the signup
            cursor.execute('''
                INSERT INTO referral_signups (referral_code, customer_email)
                VALUES (?, ?)
            ''', (referral_code, customer_email))

            # Update referral code stats
            cursor.execute('''
                UPDATE referral_codes
                SET total_signups = total_signups + 1
                WHERE referral_code = ?
            ''', (referral_code,))

            conn.commit()

            return {
                "success": True,
                "referral_code": referral_code,
                "customer_email": customer_email,
                "tier": tier,
                "commission_rate": self.get_commission_rate(tier)
            }
        finally:
            conn.close()

    def record_revenue(self, customer_email: str, revenue_amount: float) -> List[Dict]:
        """Record revenue and calculate commissions for all referrers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Find all referrals for this customer
            cursor.execute('''
                SELECT rs.id, rs.referral_code, rc.tier
                FROM referral_signups rs
                JOIN referral_codes rc ON rs.referral_code = rc.referral_code
                WHERE rs.customer_email = ? AND rs.status = 'active'
            ''', (customer_email,))

            referrals = cursor.fetchall()
            commissions = []

            for signup_id, referral_code, tier in referrals:
                commission_rate = self.get_commission_rate(tier)
                commission_amount = revenue_amount * commission_rate

                # Update signup revenue
                cursor.execute('''
                    UPDATE referral_signups
                    SET revenue_generated = revenue_generated + ?,
                        commission_paid = commission_paid + ?
                    WHERE id = ?
                ''', (revenue_amount, commission_amount, signup_id))

                # Update referral code totals
                cursor.execute('''
                    UPDATE referral_codes
                    SET total_revenue_generated = total_revenue_generated + ?,
                        total_commission_earned = total_commission_earned + ?
                    WHERE referral_code = ?
                ''', (revenue_amount, commission_amount, referral_code))

                commissions.append({
                    "referral_code": referral_code,
                    "tier": tier,
                    "revenue_amount": revenue_amount,
                    "commission_amount": commission_amount,
                    "commission_rate": commission_rate
                })

            conn.commit()
            return commissions
        finally:
            conn.close()

    def get_contributor_stats(self, referral_code: str) -> Optional[Dict]:
        """Get stats for a contributor"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT
                    referral_code,
                    contributor_email,
                    contributor_name,
                    tier,
                    total_signups,
                    total_revenue_generated,
                    total_commission_earned,
                    created_at
                FROM referral_codes
                WHERE referral_code = ?
            ''', (referral_code,))

            result = cursor.fetchone()

            if not result:
                return None

            return {
                "referral_code": result[0],
                "email": result[1],
                "name": result[2],
                "tier": result[3],
                "total_signups": result[4],
                "total_revenue_generated": result[5],
                "total_commission_earned": result[6],
                "created_at": result[7],
                "commission_rate": self.get_commission_rate(result[3])
            }
        finally:
            conn.close()

    def get_top_contributors(self, limit: int = 10) -> List[Dict]:
        """Get top contributors by commission earned"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT
                    referral_code,
                    contributor_name,
                    tier,
                    total_signups,
                    total_revenue_generated,
                    total_commission_earned
                FROM referral_codes
                ORDER BY total_commission_earned DESC
                LIMIT ?
            ''', (limit,))

            results = cursor.fetchall()

            return [{
                "referral_code": row[0],
                "name": row[1] or "Anonymous",
                "tier": row[2],
                "signups": row[3],
                "revenue_generated": row[4],
                "commission_earned": row[5]
            } for row in results]
        finally:
            conn.close()

    def get_pending_payments(self, min_amount: float = 50.0) -> List[Dict]:
        """Get contributors with pending payments above minimum threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT
                    referral_code,
                    contributor_email,
                    contributor_name,
                    total_commission_earned,
                    tier
                FROM referral_codes
                WHERE total_commission_earned >= ?
                AND referral_code NOT IN (
                    SELECT referral_code FROM commission_payments
                    WHERE status = 'paid'
                )
                ORDER BY total_commission_earned DESC
            ''', (min_amount,))

            results = cursor.fetchall()

            return [{
                "referral_code": row[0],
                "email": row[1],
                "name": row[2],
                "amount_due": row[3],
                "tier": row[4]
            } for row in results]
        finally:
            conn.close()


# Example usage and testing
if __name__ == "__main__":
    tracker = ReferralTracker()

    # Create a test referral code
    result = tracker.create_referral_code("TEST_CONTRIB_001", "test@example.com", "Test Contributor", tier=1)
    print("Created referral code:", json.dumps(result, indent=2))

    # Track a signup
    signup = tracker.track_signup("TEST_CONTRIB_001", "customer@example.com")
    print("Tracked signup:", json.dumps(signup, indent=2))

    # Record revenue (e.g., $400 from this customer)
    commissions = tracker.record_revenue("customer@example.com", 400.0)
    print("Commissions calculated:", json.dumps(commissions, indent=2))

    # Get contributor stats
    stats = tracker.get_contributor_stats("TEST_CONTRIB_001")
    print("Contributor stats:", json.dumps(stats, indent=2))

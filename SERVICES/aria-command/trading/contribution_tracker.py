# SERVICES/aria-command/trading/contribution_tracker.py
"""
Trading Contribution Tracker for TRUST Token Earning.

Members earn TRUST through trading activity per TOKENS_STRATEGY.md:
- Successful trade (profit): +5
- Weekly trading activity: +10
- Monthly profit > 5%: +25
- Referred member trades: +50

Integrates with contribution-tracker service (port 8570) for TRUST earning.
"""

import os
import sqlite3
import logging
import httpx
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# CONTRIBUTION SCORES (per TOKENS_STRATEGY.md)
# =============================================================================

CONTRIBUTION_SCORES = {
    "successful_trade": 5,      # Per profitable trade
    "weekly_activity": 10,      # Weekly trading activity bonus
    "monthly_profit_5pct": 25,  # Monthly profit > 5% bonus
    "referred_trader": 50,      # Referred member starts trading
    "loss_trade": 1,            # Even losses show participation
}


@dataclass
class TradingContribution:
    """A trading contribution record."""
    id: int
    user_id: str
    contribution_type: str
    score: int
    trade_id: Optional[str]
    details: str
    synced: bool
    created_at: datetime


class TradingContributionTracker:
    """
    Tracks trading activity for TRUST token earning.
    
    Integrates with:
    - contribution-tracker service (port 8570) for TRUST earning
    - TOKENS_STRATEGY.md contribution scores
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.db_path = Path(os.getenv(
            "CONTRIBUTION_DB_PATH",
            "/opt/fpai/aria-command/data/contributions.db"
        ))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Contribution Tracker service configuration
        self.tracker_url = os.getenv(
            "CONTRIBUTION_TRACKER_URL",
            "http://198.54.123.234:8570"
        )
        self.tracker_api_key = os.getenv("CONTRIBUTION_API_KEY", "")
        
        self._init_db()
        self._initialized = True
        logger.info("Trading Contribution Tracker initialized")
    
    def _init_db(self):
        """Initialize the contribution database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS contributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    contribution_type TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    trade_id TEXT,
                    details TEXT,
                    synced INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS user_summaries (
                    user_id TEXT PRIMARY KEY,
                    total_score INTEGER DEFAULT 0,
                    quarterly_score INTEGER DEFAULT 0,
                    successful_trades INTEGER DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    weeks_active INTEGER DEFAULT 0,
                    last_activity TEXT,
                    last_weekly_bonus TEXT,
                    last_monthly_bonus TEXT
                );
                
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id TEXT NOT NULL,
                    referred_id TEXT NOT NULL,
                    trading_started INTEGER DEFAULT 0,
                    contribution_awarded INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_contributions_user ON contributions(user_id);
                CREATE INDEX IF NOT EXISTS idx_contributions_date ON contributions(created_at);
            """)
    
    async def log_trade_contribution(
        self,
        user_id: str,
        trade_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Log a trade and calculate contribution score.
        
        Args:
            user_id: User who made the trade
            trade_result: Trade details including pnl, trade_id, etc.
        """
        pnl = trade_result.get("pnl", 0)
        trade_id = trade_result.get("trade_id", trade_result.get("id"))
        
        # Determine contribution type and score
        if pnl > 0:
            contribution_type = "successful_trade"
            score = CONTRIBUTION_SCORES["successful_trade"]
            details = f"Profitable trade: +${pnl:.2f}"
        else:
            contribution_type = "loss_trade"
            score = CONTRIBUTION_SCORES["loss_trade"]
            details = f"Trade completed: ${pnl:.2f}"
        
        # Record contribution
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Insert contribution
            conn.execute("""
                INSERT INTO contributions 
                (user_id, contribution_type, score, trade_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, contribution_type, score, trade_id, details, now.isoformat()))
            
            # Update user summary
            conn.execute("""
                INSERT INTO user_summaries (user_id, total_score, quarterly_score, 
                    successful_trades, total_trades, last_activity)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_score = total_score + excluded.total_score,
                    quarterly_score = quarterly_score + excluded.quarterly_score,
                    successful_trades = successful_trades + excluded.successful_trades,
                    total_trades = total_trades + 1,
                    last_activity = excluded.last_activity
            """, (
                user_id, 
                score, 
                score,
                1 if pnl > 0 else 0,
                now.isoformat()
            ))
        
        # Sync to contribution-tracker service
        synced = await self._sync_contribution(user_id, contribution_type, score, details)
        
        # Check for bonuses
        bonuses = await self._check_bonuses(user_id)
        
        logger.info(f"Trade contribution: {user_id} earned {score} TRUST ({contribution_type})")
        
        return {
            "success": True,
            "score": score,
            "type": contribution_type,
            "details": details,
            "synced": synced,
            "bonuses": bonuses
        }
    
    async def _check_bonuses(self, user_id: str) -> List[Dict[str, Any]]:
        """Check and award weekly/monthly bonuses."""
        bonuses = []
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            summary = conn.execute(
                "SELECT * FROM user_summaries WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if not summary:
                return bonuses
            
            # Weekly activity bonus (once per week)
            last_weekly = summary["last_weekly_bonus"]
            if not last_weekly or (now - datetime.fromisoformat(last_weekly)).days >= 7:
                # Check if user traded this week
                week_ago = (now - timedelta(days=7)).isoformat()
                trades_this_week = conn.execute("""
                    SELECT COUNT(*) FROM contributions 
                    WHERE user_id = ? AND created_at >= ?
                """, (user_id, week_ago)).fetchone()[0]
                
                if trades_this_week >= 1:
                    bonus_score = CONTRIBUTION_SCORES["weekly_activity"]
                    conn.execute("""
                        INSERT INTO contributions 
                        (user_id, contribution_type, score, details, created_at)
                        VALUES (?, 'weekly_activity', ?, 'Weekly trading activity bonus', ?)
                    """, (user_id, bonus_score, now.isoformat()))
                    
                    conn.execute("""
                        UPDATE user_summaries 
                        SET total_score = total_score + ?,
                            quarterly_score = quarterly_score + ?,
                            weeks_active = weeks_active + 1,
                            last_weekly_bonus = ?
                        WHERE user_id = ?
                    """, (bonus_score, bonus_score, now.isoformat(), user_id))
                    
                    await self._sync_contribution(
                        user_id, "weekly_activity", bonus_score, 
                        "Weekly trading activity bonus"
                    )
                    
                    bonuses.append({
                        "type": "weekly_activity",
                        "score": bonus_score,
                        "message": "Weekly trading activity bonus!"
                    })
            
            # Monthly profit bonus (once per month, if profit > 5%)
            last_monthly = summary["last_monthly_bonus"]
            if not last_monthly or (now - datetime.fromisoformat(last_monthly)).days >= 30:
                # Calculate monthly profit (would need trading P&L data)
                # For now, simplified check based on successful trade ratio
                if summary["total_trades"] >= 10:
                    win_rate = summary["successful_trades"] / summary["total_trades"]
                    if win_rate >= 0.55:  # Proxy for profitability
                        bonus_score = CONTRIBUTION_SCORES["monthly_profit_5pct"]
                        conn.execute("""
                            INSERT INTO contributions 
                            (user_id, contribution_type, score, details, created_at)
                            VALUES (?, 'monthly_profit_5pct', ?, 'Monthly profit bonus', ?)
                        """, (user_id, bonus_score, now.isoformat()))
                        
                        conn.execute("""
                            UPDATE user_summaries 
                            SET total_score = total_score + ?,
                                quarterly_score = quarterly_score + ?,
                                last_monthly_bonus = ?
                            WHERE user_id = ?
                        """, (bonus_score, bonus_score, now.isoformat(), user_id))
                        
                        await self._sync_contribution(
                            user_id, "monthly_profit_5pct", bonus_score,
                            "Monthly profit > 5% bonus!"
                        )
                        
                        bonuses.append({
                            "type": "monthly_profit_5pct",
                            "score": bonus_score,
                            "message": "Monthly profit bonus - great trading!"
                        })
        
        return bonuses
    
    async def award_referral_bonus(
        self,
        referrer_id: str,
        referred_id: str
    ) -> Dict[str, Any]:
        """Award referral bonus when referred member starts trading."""
        score = CONTRIBUTION_SCORES["referred_trader"]
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if already awarded
            existing = conn.execute("""
                SELECT id FROM referrals 
                WHERE referrer_id = ? AND referred_id = ? AND contribution_awarded = 1
            """, (referrer_id, referred_id)).fetchone()
            
            if existing:
                return {"success": False, "error": "Referral bonus already awarded"}
            
            # Record or update referral
            conn.execute("""
                INSERT INTO referrals (referrer_id, referred_id, trading_started, contribution_awarded, created_at)
                VALUES (?, ?, 1, 1, ?)
                ON CONFLICT(referrer_id, referred_id) DO UPDATE SET
                    trading_started = 1,
                    contribution_awarded = 1
            """, (referrer_id, referred_id, now.isoformat()))
            
            # Award contribution
            conn.execute("""
                INSERT INTO contributions 
                (user_id, contribution_type, score, details, created_at)
                VALUES (?, 'referred_trader', ?, ?, ?)
            """, (referrer_id, score, f"Referred trader {referred_id} started", now.isoformat()))
            
            # Update summary
            conn.execute("""
                UPDATE user_summaries 
                SET total_score = total_score + ?,
                    quarterly_score = quarterly_score + ?
                WHERE user_id = ?
            """, (score, score, referrer_id))
        
        # Sync to service
        await self._sync_contribution(
            referrer_id, "referred_trader", score,
            f"Referred member {referred_id} started trading"
        )
        
        logger.info(f"Referral bonus: {referrer_id} earned {score} TRUST for referring {referred_id}")
        
        return {
            "success": True,
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "score": score
        }
    
    async def _sync_contribution(
        self,
        user_id: str,
        contribution_type: str,
        score: int,
        details: str
    ) -> bool:
        """Sync contribution to contribution-tracker service."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.tracker_url}/api/log",
                    headers={"Authorization": f"Bearer {self.tracker_api_key}"},
                    json={
                        "member_id": user_id,
                        "type": "trading",
                        "activity": contribution_type,
                        "score": score,
                        "details": details,
                        "source": "aria_trading"
                    }
                )
                
                if response.status_code == 200:
                    # Mark as synced
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            UPDATE contributions 
                            SET synced = 1 
                            WHERE user_id = ? AND created_at = (
                                SELECT MAX(created_at) FROM contributions WHERE user_id = ?
                            )
                        """, (user_id, user_id))
                    return True
                    
        except Exception as e:
            logger.warning(f"Failed to sync contribution to tracker service: {e}")
        
        return False
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get contribution summary for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            summary = conn.execute(
                "SELECT * FROM user_summaries WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if not summary:
                return {
                    "user_id": user_id,
                    "total_score": 0,
                    "quarterly_score": 0,
                    "tier": "inactive",
                    "eligible_for_benefits": False
                }
            
            summary_dict = dict(summary)
            
            # Determine tier based on quarterly score
            quarterly = summary_dict.get("quarterly_score", 0)
            if quarterly >= 100:
                tier = "active"
                eligible = True
            elif quarterly >= 50:
                tier = "engaged"
                eligible = False  # Reduced eligibility
            else:
                tier = "inactive"
                eligible = False
            
            summary_dict["tier"] = tier
            summary_dict["eligible_for_benefits"] = eligible
            summary_dict["minimum_for_benefits"] = 100
            summary_dict["points_to_active"] = max(0, 100 - quarterly)
            
            return summary_dict
    
    def get_recent_contributions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[TradingContribution]:
        """Get recent contributions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM contributions 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            
            return [
                TradingContribution(
                    id=row["id"],
                    user_id=row["user_id"],
                    contribution_type=row["contribution_type"],
                    score=row["score"],
                    trade_id=row["trade_id"],
                    details=row["details"],
                    synced=bool(row["synced"]),
                    created_at=datetime.fromisoformat(row["created_at"])
                )
                for row in rows
            ]
    
    def reset_quarterly_scores(self):
        """Reset quarterly scores (run at end of each quarter)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE user_summaries SET quarterly_score = 0")
        logger.info("Reset quarterly scores for all users")


# Singleton instance
_tracker: Optional[TradingContributionTracker] = None


def get_contribution_tracker() -> TradingContributionTracker:
    """Get the singleton contribution tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = TradingContributionTracker()
    return _tracker


async def log_trade_contribution(
    user_id: str,
    trade_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Log a trade and calculate contribution score."""
    return await get_contribution_tracker().log_trade_contribution(user_id, trade_result)


def get_user_contribution_summary(user_id: str) -> Dict[str, Any]:
    """Get contribution summary for a user."""
    return get_contribution_tracker().get_user_summary(user_id)










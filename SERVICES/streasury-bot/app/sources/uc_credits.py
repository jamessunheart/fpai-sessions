"""
UC Credits adapter for STreasury Bot.
Syncs trading fees, subscription revenue, and credit activities from ARIA billing.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Import the billing manager from aria-command
sys.path.append('/opt/fpai/aria-command')
try:
    from billing.uc_billing import get_billing_manager, get_commons_contribution_summary
except ImportError:
    # Fallback for local development
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'aria-command'))
    from billing.uc_billing import get_billing_manager, get_commons_contribution_summary

from .base import Adapter, SyncResult

logger = logging.getLogger(__name__)


@dataclass 
class UCTransaction:
    """UC credit transaction for treasury tracking."""
    user_id: str
    transaction_type: str  # subscription, performance_fee, credit_add, etc.
    amount: float
    description: str
    created_at: datetime
    reference_id: Optional[str]


class UCCreditsAdapter(Adapter):
    """Syncs UC credit activities to STreasury Bot ledger."""
    
    def __init__(self, connection_id: int, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.billing_manager = get_billing_manager()
        
        # Get sync start point from config
        self.since = config.get('since', '2025-01-01')
        if isinstance(self.since, str):
            self.since = datetime.fromisoformat(self.since)
    
    async def fetch_transactions(self) -> List[UCTransaction]:
        """Fetch new UC transactions since last sync."""
        transactions = []
        
        # Read directly from billing DB (faster than individual API calls)
        db_path = self.billing_manager.db_path
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all transactions since last sync
            rows = conn.execute("""
                SELECT * FROM transactions 
                WHERE created_at > ? 
                ORDER BY created_at ASC
            """, (self.since.isoformat(),)).fetchall()
            
            for row in rows:
                transactions.append(UCTransaction(
                    user_id=row['user_id'],
                    transaction_type=row['transaction_type'],
                    amount=float(row['amount']),
                    description=row['description'] or 'UC transaction',
                    created_at=datetime.fromisoformat(row['created_at']),
                    reference_id=row['reference_id']
                ))
        
        logger.info(f"Fetched {len(transactions)} UC transactions since {self.since}")
        return transactions
    
    async def sync_commons_contributions(self) -> List[Dict[str, Any]]:
        """Sync Commons Reserve contributions as treasury income."""
        contributions = []
        
        try:
            commons_summary = await get_commons_contribution_summary()
            
            # Convert recent contributions to treasury entries
            for contrib in commons_summary.get('recent', []):
                contributions.append({
                    'amount': float(contrib['commons_amount']),
                    'account': 'system:commons',
                    'category': 'revenue:trading_fees',
                    'vendor': f"UC Trading Fees ({contrib['fee_type']})",
                    'date': contrib['created_at'],
                    'memo': f"Commons allocation from {contrib['fee_type']} fee (30%)",
                    'source_ref': f"commons_{contrib['id']}"
                })
                
        except Exception as e:
            logger.warning(f"Failed to sync commons contributions: {e}")
        
        return contributions
    
    def convert_to_ledger_entry(self, tx: UCTransaction) -> Dict[str, Any]:
        """Convert UC transaction to STreasury ledger format."""
        
        # Map transaction types to accounts and categories
        mapping = {
            'subscription': {
                'account': 'revenue:subscriptions',
                'category': 'revenue:monthly',
                'vendor': 'ARIA Steward Subscription'
            },
            'performance_fee': {
                'account': 'revenue:trading',
                'category': 'revenue:performance',
                'vendor': 'ARIA Trustee Performance Fee'
            },
            'credit_add': {
                'account': 'revenue:credits',
                'category': 'revenue:credits',
                'vendor': 'UC Credit Purchase'
            },
            'refund': {
                'account': 'expenses:refunds',
                'category': 'expenses:customer_care',
                'vendor': 'UC Refund'
            }
        }
        
        entry_config = mapping.get(tx.transaction_type, {
            'account': 'revenue:misc',
            'category': 'revenue:other',
            'vendor': 'UC Transaction'
        })
        
        # Revenue is positive in treasury, expenses negative
        amount = abs(tx.amount) if tx.transaction_type in ['subscription', 'performance_fee', 'credit_add'] else -abs(tx.amount)
        
        return {
            'amount': amount,
            'account': entry_config['account'],
            'category': entry_config['category'],
            'vendor': entry_config['vendor'],
            'date': tx.created_at.strftime('%Y-%m-%d'),
            'memo': f"{tx.description} (User: {tx.user_id})",
            'source_ref': f"uc_{tx.reference_id or tx.user_id}_{int(tx.created_at.timestamp())}"
        }
    
    async def sync(self) -> SyncResult:
        """Main sync method."""
        result = SyncResult()
        
        try:
            # 1. Sync UC credit transactions
            transactions = await self.fetch_transactions()
            
            for tx in transactions:
                ledger_entry = self.convert_to_ledger_entry(tx)
                
                # Insert into STreasury ledger (via the base insert method)
                await self.insert_transaction(
                    source='uc_credits',
                    source_ref=ledger_entry['source_ref'],
                    amount=ledger_entry['amount'],
                    account=ledger_entry['account'],
                    category=ledger_entry['category'],
                    vendor=ledger_entry['vendor'],
                    memo=ledger_entry['memo'],
                    date=ledger_entry['date']
                )
                
                result.inserted += 1
                result.seen += 1
            
            # 2. Sync Commons contributions
            commons_entries = await self.sync_commons_contributions()
            
            for entry in commons_entries:
                await self.insert_transaction(
                    source='uc_credits',
                    source_ref=entry['source_ref'],
                    amount=entry['amount'],
                    account=entry['account'],
                    category=entry['category'],
                    vendor=entry['vendor'],
                    memo=entry['memo'],
                    date=entry['date']
                )
                
                result.inserted += 1
                result.seen += 1
            
            # 3. Update sync checkpoint
            if transactions:
                latest_tx = max(transactions, key=lambda t: t.created_at)
                await self.update_sync_checkpoint(latest_tx.created_at)
            
            logger.info(f"UC Credits sync completed: {result.inserted} inserted, {result.seen} seen")
            
        except Exception as e:
            logger.error(f"UC Credits sync failed: {e}")
            result.error = str(e)
        
        return result
    
    async def update_sync_checkpoint(self, latest_datetime: datetime):
        """Update the sync checkpoint for next run."""
        # This should update the source_connection config
        # Implementation depends on base class methods
        self.since = latest_datetime
        # Update config in DB would go here
        pass


# Register the adapter
def create_adapter(connection_id: int, config: Dict[str, Any]) -> UCCreditsAdapter:
    """Factory function for creating UC Credits adapter."""
    return UCCreditsAdapter(connection_id, config)
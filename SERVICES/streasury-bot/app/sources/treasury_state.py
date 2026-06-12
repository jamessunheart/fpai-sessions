"""
Treasury State adapter for STreasury Bot.
Syncs core treasury state (positions, TVL, magnet engine status) to ledger and KPIs.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from .base import Adapter, SyncResult

logger = logging.getLogger(__name__)


class TreasuryStateAdapter(Adapter):
    """Syncs core treasury state to STreasury Bot KPIs and holdings."""
    
    def __init__(self, connection_id: int, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        
        # Path to treasury state file
        self.state_file = Path(config.get('treasury_file', '/opt/fpai/core/STATE/TREASURY.json'))
        
        # Track last sync to avoid duplicate KPI updates
        self.last_sync = config.get('last_sync', None)
        if self.last_sync:
            self.last_sync = datetime.fromisoformat(self.last_sync)
    
    async def load_treasury_state(self) -> Optional[Dict[str, Any]]:
        """Load current treasury state from JSON file."""
        try:
            if not self.state_file.exists():
                logger.warning(f"Treasury state file not found: {self.state_file}")
                return None
                
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                
            logger.info(f"Loaded treasury state: TVL=${state.get('tvl', 0):,.2f}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load treasury state: {e}")
            return None
    
    async def sync_kpis(self, state: Dict[str, Any]) -> int:
        """Sync key treasury metrics as STreasury Bot KPIs."""
        kpi_updates = 0
        
        try:
            # Core treasury KPIs
            kpis = {
                'TVL': state.get('tvl', 0),
                'PnL_24h': state.get('pnl_24h', 0),
                'PnL_Percent': state.get('pnl_percent', 0),
                'Cash_Position': state.get('cash', 0),
                'Allocation_Stable': state.get('allocation', {}).get('stable', 0),
                'Allocation_BlueChip': state.get('allocation', {}).get('blue_chip', 0), 
                'Allocation_Moonshot': state.get('allocation', {}).get('moonshot', 0),
            }
            
            # Magnet engine metrics
            magnet = state.get('magnet_engine', {})
            if magnet:
                kpis.update({
                    'Magnet_Strength': magnet.get('magnet_strength', 0),
                    'Magnet_Leverage': magnet.get('leverage', 1.0),
                    'Magnet_Target_Leverage': magnet.get('target_leverage', 1.0),
                    'Magnet_Distance': magnet.get('distance', 0),
                    'Magnet_Conflict': magnet.get('conflict', 0),
                    'Magnet_Volatility': magnet.get('volatility', 0),
                })
            
            # Insert each KPI via STreasury Bot's KPI system
            for kpi_name, value in kpis.items():
                await self.update_kpi(kpi_name, float(value))
                kpi_updates += 1
                
            logger.info(f"Updated {kpi_updates} treasury KPIs")
            
        except Exception as e:
            logger.error(f"Failed to sync KPIs: {e}")
        
        return kpi_updates
    
    async def sync_holdings(self, state: Dict[str, Any]) -> int:
        """Sync position holdings as STreasury Bot crypto holdings."""
        holdings_updates = 0
        
        try:
            positions = state.get('positions', [])
            
            for pos in positions:
                asset = pos.get('asset', 'UNKNOWN')
                size_usd = pos.get('size_usd', 0)
                protocol = pos.get('protocol', '')
                apy = pos.get('apy', 0)
                
                # Convert USD value to asset quantity (approximate)
                # For now, we'll track USD values and note the protocol
                memo = f"{protocol} position (APY: {apy*100:.1f}%)" if protocol else "Position"
                
                await self.update_crypto_holding(
                    asset=asset,
                    usd_value=size_usd,
                    memo=memo
                )
                
                holdings_updates += 1
                
            logger.info(f"Updated {holdings_updates} treasury holdings")
            
        except Exception as e:
            logger.error(f"Failed to sync holdings: {e}")
        
        return holdings_updates
    
    async def sync_magnet_status(self, state: Dict[str, Any]) -> bool:
        """Log magnet engine status changes as treasury events."""
        try:
            magnet = state.get('magnet_engine', {})
            if not magnet:
                return False
            
            status = magnet.get('status', 'UNKNOWN')
            message = magnet.get('message', '')
            
            # Check if this is a status change worth logging
            status_memo = f"Magnet Engine: {status}"
            if message:
                status_memo += f" - {message}"
            
            # Log as a $0 transaction for record-keeping
            await self.insert_transaction(
                source='treasury_state',
                source_ref=f"magnet_status_{datetime.now().strftime('%Y%m%d_%H%M')}",
                amount=0.0,
                account='system:magnet_engine',
                category='system:status',
                vendor='Treasury Magnet Engine',
                memo=status_memo,
                date=datetime.now().strftime('%Y-%m-%d')
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync magnet status: {e}")
            return False
    
    async def update_kpi(self, name: str, value: float):
        """Update a KPI in STreasury Bot (placeholder - implement based on actual KPI API)."""
        # This would integrate with STreasury Bot's KPI system
        # For now, logging the intent
        logger.info(f"KPI Update: {name} = {value}")
        # TODO: Implement actual KPI update via STreasury Bot API or direct DB
        pass
    
    async def update_crypto_holding(self, asset: str, usd_value: float, memo: str = ""):
        """Update crypto holding in STreasury Bot."""
        # This would integrate with STreasury Bot's holdings system
        logger.info(f"Holding Update: {asset} = ${usd_value:,.2f} ({memo})")
        # TODO: Implement actual holding update via STreasury Bot API
        pass
    
    async def sync(self) -> SyncResult:
        """Main sync method."""
        result = SyncResult()
        
        try:
            # Load current treasury state
            state = await self.load_treasury_state()
            if not state:
                result.error = "Could not load treasury state file"
                return result
            
            result.seen = 1  # We saw one state file
            
            # 1. Sync KPIs (TVL, PnL, allocations, magnet metrics)
            kpi_count = await self.sync_kpis(state)
            
            # 2. Sync position holdings
            holdings_count = await self.sync_holdings(state)
            
            # 3. Log magnet status if notable
            magnet_logged = await self.sync_magnet_status(state)
            
            # Count successful operations
            result.inserted = kpi_count + holdings_count + (1 if magnet_logged else 0)
            
            # Update last sync timestamp
            await self.update_sync_checkpoint(datetime.now())
            
            logger.info(f"Treasury state sync completed: {result.inserted} items updated")
            
        except Exception as e:
            logger.error(f"Treasury state sync failed: {e}")
            result.error = str(e)
        
        return result
    
    async def update_sync_checkpoint(self, sync_time: datetime):
        """Update last sync timestamp."""
        self.last_sync = sync_time
        # TODO: Update config in source_connection table
        pass


def create_adapter(connection_id: int, config: Dict[str, Any]) -> TreasuryStateAdapter:
    """Factory function for creating Treasury State adapter."""
    return TreasuryStateAdapter(connection_id, config)
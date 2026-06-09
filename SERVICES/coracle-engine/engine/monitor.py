"""
Coracle Prediction Engine - Contract Monitor
=============================================
Background task that continuously monitors for valid trading setups
and triggers alerts when the Sacred Gate passes.
"""
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional

from app.config import get_settings
from engine.alerter import get_alerter

logger = logging.getLogger(__name__)


class ContractMonitor:
    """
    Continuously monitors all tracked assets for valid trading setups.
    When the Sacred Gate passes, sends an alert via Telegram.
    
    Uses the internal /api/analyze endpoint to leverage all existing logic.
    """
    
    def __init__(self, check_interval_seconds: int = 30):
        self.settings = get_settings()
        self.check_interval = check_interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.base_url = f"http://localhost:{self.settings.port}"
    
    async def check_asset(self, symbol: str) -> Optional[dict]:
        """
        Check a single asset for a valid trading setup.
        Returns the contract if Sacred Gate passes, None otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/analyze",
                    json={"ticker": symbol}
                )
                
                if response.status_code != 200:
                    logger.warning(f"Analyze endpoint returned {response.status_code} for {symbol}")
                    return None
                
                result = response.json()
                
                # Check if gate passed and contract was generated
                if result.get("success") and result.get("contract"):
                    logger.info(f"✅ Valid contract generated for {symbol}!")
                    return {
                        "contract": result["contract"],
                        "signals": result.get("signals", {}),
                        "gate_status": result.get("gate_status", {}),
                        "confluence": result.get("confluence", {})
                    }
                else:
                    # Gate failed or no contract
                    gate = result.get("gate_status", {})
                    keys = gate.get("keys_passed", 0)
                    logger.debug(f"{symbol}: Gate {keys}/3 - no contract")
                    return None
                    
        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")
            return None
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info(f"🔮 Contract Monitor started - checking every {self.check_interval}s")
        
        alerter = get_alerter()
        
        # Wait a bit for the app to fully start
        await asyncio.sleep(5)
        
        while self.running:
            try:
                for symbol in self.settings.tracked_assets:
                    result = await self.check_asset(symbol)
                    
                    if result:
                        contract = result["contract"]
                        signals = result["signals"]
                        
                        # Send alert
                        if alerter:
                            await alerter.send_alert(contract, signals)
                        else:
                            logger.warning("Alerter not configured - contract not sent")
                    
                    # Small delay between assets to avoid hammering the API
                    await asyncio.sleep(2)
                
                # Wait for next check cycle
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
        
        logger.info("Contract Monitor stopped")
    
    def start(self):
        """Start the monitor as a background task."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
    
    def stop(self):
        """Stop the monitor."""
        self.running = False
        if self._task:
            self._task.cancel()


# Singleton instance
_monitor: Optional[ContractMonitor] = None


def get_monitor() -> ContractMonitor:
    """Get or create the monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ContractMonitor()
    return _monitor

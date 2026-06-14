"""
REVENUE SENSOR
==============

Monitors business metrics and revenue opportunities.

Watches:
- Credit transactions
- Service usage
- Customer activity
- Growth metrics
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx

from ..proactive import Signal, Priority, ActionType

logger = logging.getLogger("aria.sensors.revenue")

# Endpoints
CREDITS_GATEWAY_URL = os.getenv("CREDITS_GATEWAY_URL", "http://198.54.123.234:8765")
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://198.54.123.234:8700")


class RevenueSensor:
    """
    Sensor for revenue and business metrics.
    
    Monitors:
    - Credit transactions
    - New customer activity
    - Service usage patterns
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=15.0)
        self.last_transaction_count = None
        self.last_customer_count = None
        logger.info("RevenueSensor initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def sense(self) -> List[Signal]:
        """
        Sense revenue state and generate signals.
        
        Returns list of signals detected.
        """
        signals = []
        
        # 1. Check credit transactions
        transaction_signals = await self._check_transactions()
        signals.extend(transaction_signals)
        
        # 2. Check for new customers
        customer_signals = await self._check_customers()
        signals.extend(customer_signals)
        
        # 3. Check service usage
        usage_signals = await self._check_usage()
        signals.extend(usage_signals)
        
        return signals
    
    async def _check_transactions(self) -> List[Signal]:
        """Check for new credit transactions."""
        signals = []
        
        try:
            r = await self.http.get(
                f"{CREDITS_GATEWAY_URL}/api/transactions/recent",
                timeout=10.0
            )
            
            if r.status_code == 200:
                data = r.json()
                transactions = data.get("transactions", [])
                count = len(transactions)
                total_value = sum(t.get("amount", 0) for t in transactions)
                
                # Check for significant new activity
                if self.last_transaction_count is not None:
                    new_transactions = count - self.last_transaction_count
                    
                    if new_transactions > 0 and total_value > 0:
                        signals.append(Signal(
                            source="revenue",
                            signal_type="new_transactions",
                            priority=Priority.LOW,
                            title=f"💳 {new_transactions} New Transaction(s)",
                            description=f"Total value: {total_value:.2f} UC",
                            data={
                                "new_count": new_transactions,
                                "total_value": total_value
                            },
                            action_type=ActionType.NOTIFY
                        ))
                
                self.last_transaction_count = count
        
        except Exception as e:
            logger.debug(f"Transaction check error: {e}")
        
        return signals
    
    async def _check_customers(self) -> List[Signal]:
        """Check for new customers."""
        signals = []
        
        try:
            r = await self.http.get(
                f"{CREDITS_GATEWAY_URL}/api/customers/stats",
                timeout=10.0
            )
            
            if r.status_code == 200:
                data = r.json()
                total_customers = data.get("total_customers", 0)
                active_today = data.get("active_today", 0)
                
                # Check for new customers
                if self.last_customer_count is not None:
                    new_customers = total_customers - self.last_customer_count
                    
                    if new_customers > 0:
                        signals.append(Signal(
                            source="revenue",
                            signal_type="new_customers",
                            priority=Priority.MEDIUM,
                            title=f"🎉 {new_customers} New Customer(s)!",
                            description=f"Total: {total_customers} customers, {active_today} active today",
                            data={
                                "new_count": new_customers,
                                "total": total_customers,
                                "active_today": active_today
                            },
                            action_type=ActionType.NOTIFY
                        ))
                
                self.last_customer_count = total_customers
        
        except Exception as e:
            logger.debug(f"Customer check error: {e}")
        
        return signals
    
    async def _check_usage(self) -> List[Signal]:
        """Check service usage patterns."""
        signals = []
        
        try:
            r = await self.http.get(
                f"{ANALYTICS_URL}/api/usage/summary",
                timeout=10.0
            )
            
            if r.status_code == 200:
                data = r.json()
                
                # Look for usage spikes or drops
                api_calls = data.get("api_calls_today", 0)
                vs_average = data.get("vs_7day_average", 0)  # % change
                
                if vs_average > 50:
                    signals.append(Signal(
                        source="revenue",
                        signal_type="usage_spike",
                        priority=Priority.MEDIUM,
                        title=f"📈 Usage Spike: +{vs_average:.0f}% vs average",
                        description=f"{api_calls} API calls today, significantly above normal",
                        data={
                            "api_calls": api_calls,
                            "vs_average": vs_average
                        },
                        action_type=ActionType.NOTIFY
                    ))
                elif vs_average < -50:
                    signals.append(Signal(
                        source="revenue",
                        signal_type="usage_drop",
                        priority=Priority.MEDIUM,
                        title=f"📉 Usage Drop: {vs_average:.0f}% vs average",
                        description=f"Only {api_calls} API calls today, significantly below normal",
                        data={
                            "api_calls": api_calls,
                            "vs_average": vs_average
                        },
                        action_type=ActionType.NOTIFY
                    ))
        
        except Exception as e:
            logger.debug(f"Usage check error: {e}")
        
        return signals
    
    async def get_status(self) -> Dict:
        """Get sensor status."""
        return {
            "name": "revenue",
            "last_transaction_count": self.last_transaction_count,
            "last_customer_count": self.last_customer_count,
            "credits_url": CREDITS_GATEWAY_URL,
            "analytics_url": ANALYTICS_URL
        }



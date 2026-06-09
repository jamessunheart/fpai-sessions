#!/usr/bin/env python3
"""
External Signal Aggregator
==========================
Aggregates external signals that indicate stress or calm.

Signals:
- Trading risk (liquidation, funding rates)
- System health (services down = external stress)
- Time of day (late night activity = strain)
- Market conditions (high volatility = stress environment)
"""
import os
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("cis.sensors.external")

@dataclass
class ExternalSignal:
    stress_level: str  # low, medium, high
    factors: List[str]  # what's contributing to stress
    signals: Dict  # raw signal data
    source: str = "external"


class ExternalSensor:
    """Aggregates external stress signals."""
    
    def __init__(self):
        self.creds_path = "/opt/fpai/hyperliquid_credentials.json"
        self._load_credentials()
    
    def _load_credentials(self):
        try:
            with open(self.creds_path) as f:
                creds = json.load(f)
                self.account = creds.get("main_account")
        except:
            self.account = None
    
    def _check_liquidation_risk(self) -> Dict:
        """Check if account is near liquidation."""
        if not self.account:
            return {"at_risk": False, "margin_ratio": None}
        
        try:
            import requests
            r = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": self.account},
                timeout=10
            )
            state = r.json()
            margin = state.get("marginSummary", {})
            
            account_value = float(margin.get("accountValue", 1))
            margin_used = float(margin.get("totalMarginUsed", 0))
            
            if account_value == 0:
                return {"at_risk": False, "margin_ratio": 0}
            
            margin_ratio = margin_used / account_value
            
            return {
                "at_risk": margin_ratio > 0.8,  # 80%+ margin used is risky
                "margin_ratio": margin_ratio,
                "account_value": account_value
            }
        except Exception as e:
            logger.debug(f"Could not check liquidation risk: {e}")
            return {"at_risk": False, "margin_ratio": None}
    
    def _check_system_health(self) -> Dict:
        """Check if key services are healthy."""
        services = [
            "fpai-aria",
            "fpai-level10-trader",
            "fpai-jai-auto"
        ]
        
        unhealthy = []
        for svc in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout.strip() != "active":
                    unhealthy.append(svc)
            except:
                pass  # Can't check, assume fine
        
        return {
            "all_healthy": len(unhealthy) == 0,
            "unhealthy_services": unhealthy
        }
    
    def _check_time_stress(self) -> Dict:
        """Check if current time suggests stress."""
        now = datetime.now()
        hour = now.hour
        
        # Late night (11pm - 6am) = potential stress if active
        is_late_night = hour >= 23 or hour < 6
        
        # Early morning (6am - 9am) = transition time
        is_early_morning = 6 <= hour < 9
        
        # Day of week
        is_weekend = now.weekday() >= 5
        
        return {
            "is_late_night": is_late_night,
            "is_early_morning": is_early_morning,
            "is_weekend": is_weekend,
            "hour": hour
        }
    
    def _check_market_volatility(self) -> Dict:
        """Check current market volatility."""
        try:
            import requests
            
            # Get BTC price changes (proxy for market volatility)
            r = requests.get(
                "http://198.54.123.234:8600/api/liquidity-clarity",
                timeout=10
            )
            data = r.json()
            
            symbols = data.get("symbols", {})
            btc = symbols.get("BTC/USDT", {})
            sol = symbols.get("SOL/USDT", {})
            
            # Bias strength indicates directional pressure
            btc_pressure = btc.get("bias_strength", 0)
            sol_pressure = sol.get("bias_strength", 0)
            
            high_volatility = btc_pressure > 50 or sol_pressure > 50
            
            return {
                "high_volatility": high_volatility,
                "btc_pressure": btc_pressure,
                "sol_pressure": sol_pressure
            }
        except Exception as e:
            logger.debug(f"Could not check market volatility: {e}")
            return {"high_volatility": False}
    
    def sense(self) -> ExternalSignal:
        """Aggregate all external signals."""
        signals = {}
        factors = []
        
        # Check liquidation risk
        liq = self._check_liquidation_risk()
        signals["liquidation"] = liq
        if liq.get("at_risk"):
            factors.append("high_margin_usage")
        
        # Check system health
        health = self._check_system_health()
        signals["system_health"] = health
        if not health.get("all_healthy"):
            factors.append("services_unhealthy")
        
        # Check time
        time_check = self._check_time_stress()
        signals["time"] = time_check
        if time_check.get("is_late_night"):
            factors.append("late_night_activity")
        
        # Check market
        market = self._check_market_volatility()
        signals["market"] = market
        if market.get("high_volatility"):
            factors.append("high_market_volatility")
        
        # Determine overall stress level
        if len(factors) >= 3:
            stress_level = "high"
        elif len(factors) >= 1:
            stress_level = "medium"
        else:
            stress_level = "low"
        
        return ExternalSignal(
            stress_level=stress_level,
            factors=factors,
            signals=signals
        )


# Singleton
_sensor: Optional[ExternalSensor] = None

def get_external_sensor() -> ExternalSensor:
    global _sensor
    if _sensor is None:
        _sensor = ExternalSensor()
    return _sensor

def sense_external() -> ExternalSignal:
    """Sense external stress factors."""
    return get_external_sensor().sense()









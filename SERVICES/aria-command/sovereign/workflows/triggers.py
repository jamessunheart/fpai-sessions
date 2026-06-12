#!/usr/bin/env python3
"""
ARIA ULTRA POWER - TRIGGER SYSTEM
==================================

Trigger types for workflow automation:
- Price triggers (asset price conditions)
- Time triggers (scheduled/cron-style)
- Event triggers (server events, trading events)
- Compound triggers (AND/OR logic)
"""

import asyncio
import logging
import re
import time
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("aria.workflows.triggers")

# Configuration
WHALETRACK_URL = "http://198.54.123.234:8600"


class TriggerType(Enum):
    """Types of triggers."""
    PRICE = "price"
    TIME = "time"
    EVENT = "event"
    COMPOUND = "compound"
    INTERVAL = "interval"
    SERVER = "server"


@dataclass
class Trigger:
    """Base trigger definition."""
    type: TriggerType
    config: Dict
    last_checked: Optional[float] = None
    last_triggered: Optional[float] = None


@dataclass
class PriceTrigger(Trigger):
    """Price-based trigger."""
    asset: str = ""
    condition: str = ""  # e.g., "< 120", "> 150", "crosses 130"
    
    def __post_init__(self):
        self.type = TriggerType.PRICE


@dataclass
class TimeTrigger(Trigger):
    """Time-based trigger."""
    schedule: str = ""  # Cron-style or simple format
    timezone: str = "UTC"
    
    def __post_init__(self):
        self.type = TriggerType.TIME


@dataclass
class EventTrigger(Trigger):
    """Event-based trigger."""
    event_type: str = ""  # "server_memory", "trade_executed", etc.
    condition: str = ""
    
    def __post_init__(self):
        self.type = TriggerType.EVENT


@dataclass
class CompoundTrigger(Trigger):
    """Compound trigger with AND/OR logic."""
    operator: str = "AND"  # AND or OR
    triggers: List[Dict] = None
    
    def __post_init__(self):
        self.type = TriggerType.COMPOUND
        if self.triggers is None:
            self.triggers = []


# Price cache to avoid excessive API calls
_price_cache: Dict[str, Tuple[float, float]] = {}  # asset -> (price, timestamp)
_price_cache_ttl = 10  # seconds


async def get_current_price(asset: str) -> Optional[float]:
    """Get current price for an asset."""
    global _price_cache
    
    asset_upper = asset.upper()
    current_time = time.time()
    
    # Check cache
    if asset_upper in _price_cache:
        price, cached_at = _price_cache[asset_upper]
        if current_time - cached_at < _price_cache_ttl:
            return price
    
    # Fetch from WhaleTrack
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{WHALETRACK_URL}/api/liquidity-clarity")
            if response.status_code == 200:
                data = response.json()
                symbols = data.get("symbols", {})
                
                # Try different key formats
                for key in [f"{asset_upper}/USDT", asset_upper, f"{asset_upper}USDT"]:
                    if key in symbols:
                        price = symbols[key].get("price", 0)
                        _price_cache[asset_upper] = (price, current_time)
                        return price
                
                logger.warning(f"Asset {asset} not found in price data")
                return None
    except Exception as e:
        logger.error(f"Error fetching price for {asset}: {e}")
        return None


def parse_condition(condition: str, current_value: float) -> bool:
    """
    Parse and evaluate a condition string.
    
    Supports:
    - "< 120" - less than
    - "> 150" - greater than
    - "<= 120" - less than or equal
    - ">= 150" - greater than or equal
    - "== 130" - equals
    - "!= 130" - not equals
    - "between 120 and 150" - range
    - "crosses 130" - would need previous value (simplified to equals-ish)
    """
    condition = condition.strip()
    
    # Less than or equal
    if match := re.match(r'^<=?\s*([\d.]+)$', condition):
        threshold = float(match.group(1))
        return current_value <= threshold if '=' in condition else current_value < threshold
    
    # Greater than or equal
    if match := re.match(r'^>=?\s*([\d.]+)$', condition):
        threshold = float(match.group(1))
        return current_value >= threshold if '=' in condition else current_value > threshold
    
    # Equals
    if match := re.match(r'^==?\s*([\d.]+)$', condition):
        threshold = float(match.group(1))
        return abs(current_value - threshold) < 0.01 * threshold  # 1% tolerance
    
    # Not equals
    if match := re.match(r'^!=\s*([\d.]+)$', condition):
        threshold = float(match.group(1))
        return abs(current_value - threshold) >= 0.01 * threshold
    
    # Between
    if match := re.match(r'^between\s+([\d.]+)\s+and\s+([\d.]+)$', condition, re.IGNORECASE):
        low = float(match.group(1))
        high = float(match.group(2))
        return low <= current_value <= high
    
    # Crosses (simplified - triggers when near the value)
    if match := re.match(r'^crosses?\s+([\d.]+)$', condition, re.IGNORECASE):
        threshold = float(match.group(1))
        return abs(current_value - threshold) < 0.005 * threshold  # 0.5% tolerance
    
    logger.warning(f"Unknown condition format: {condition}")
    return False


async def evaluate_price_trigger(config: Dict) -> Tuple[bool, Dict]:
    """Evaluate a price trigger."""
    asset = config.get("asset", "").upper()
    condition = config.get("condition", "")
    
    if not asset or not condition:
        return False, {}
    
    current_price = await get_current_price(asset)
    if current_price is None:
        return False, {}
    
    triggered = parse_condition(condition, current_price)
    
    return triggered, {
        "asset": asset,
        "condition": condition,
        "current_price": current_price,
        "triggered": triggered,
    }


async def evaluate_time_trigger(config: Dict) -> Tuple[bool, Dict]:
    """
    Evaluate a time trigger.
    
    Supports:
    - "every 5m" - every 5 minutes
    - "every 1h" - every hour
    - "at 09:00" - at specific time
    - "daily at 09:00" - daily at specific time
    - Cron-style: "0 9 * * *" (9am daily)
    """
    schedule = config.get("schedule", "")
    last_triggered = config.get("last_triggered", 0)
    
    now = datetime.now()
    current_time = time.time()
    
    # "every Xm" or "every Xh"
    if match := re.match(r'^every\s+(\d+)\s*([mh])$', schedule, re.IGNORECASE):
        value = int(match.group(1))
        unit = match.group(2).lower()
        
        interval_seconds = value * 60 if unit == 'm' else value * 3600
        
        if current_time - last_triggered >= interval_seconds:
            return True, {"schedule": schedule, "time": now.isoformat()}
        return False, {}
    
    # "at HH:MM" or "daily at HH:MM"
    if match := re.match(r'^(?:daily\s+)?at\s+(\d{1,2}):(\d{2})$', schedule, re.IGNORECASE):
        target_hour = int(match.group(1))
        target_minute = int(match.group(2))
        
        # Check if we're at the target time (within 1 minute window)
        if now.hour == target_hour and now.minute == target_minute:
            # Check we haven't already triggered today
            if last_triggered:
                last_dt = datetime.fromtimestamp(last_triggered)
                if last_dt.date() == now.date():
                    return False, {}
            
            return True, {"schedule": schedule, "time": now.isoformat()}
        return False, {}
    
    # Simple cron (minute hour day month weekday)
    if re.match(r'^[\d*,/-]+\s+[\d*,/-]+\s+[\d*,/-]+\s+[\d*,/-]+\s+[\d*,/-]+$', schedule):
        # Basic cron parsing
        parts = schedule.split()
        minute, hour, day, month, weekday = parts
        
        matches = True
        
        if minute != '*' and now.minute != int(minute):
            matches = False
        if hour != '*' and now.hour != int(hour):
            matches = False
        if day != '*' and now.day != int(day):
            matches = False
        if month != '*' and now.month != int(month):
            matches = False
        if weekday != '*' and now.weekday() != int(weekday):
            matches = False
        
        if matches:
            # Check cooldown (at least 60 seconds between triggers)
            if current_time - last_triggered >= 60:
                return True, {"schedule": schedule, "time": now.isoformat()}
        
        return False, {}
    
    return False, {}


async def evaluate_event_trigger(config: Dict) -> Tuple[bool, Dict]:
    """
    Evaluate an event trigger.
    
    Supported events:
    - server_memory: condition on memory usage
    - server_disk: condition on disk usage
    - server_load: condition on CPU load
    - trade_executed: when a trade executes
    - position_opened: when a position opens
    - position_closed: when a position closes
    """
    event_type = config.get("event_type", "")
    condition = config.get("condition", "")
    
    if event_type == "server_memory":
        # Check server memory
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check primary server
                response = await client.get("http://198.54.123.234:8600/health")
                if response.status_code == 200:
                    # Get memory from system
                    # This is a placeholder - would need actual memory check
                    memory_percent = 75  # Would be dynamic
                    triggered = parse_condition(condition, memory_percent)
                    return triggered, {"event": event_type, "memory_percent": memory_percent}
        except:
            pass
        return False, {}
    
    if event_type == "server_disk":
        # Similar pattern for disk
        disk_percent = 50  # Placeholder
        triggered = parse_condition(condition, disk_percent)
        return triggered, {"event": event_type, "disk_percent": disk_percent}
    
    # Other event types would subscribe to event queues
    return False, {}


async def evaluate_compound_trigger(config: Dict) -> Tuple[bool, Dict]:
    """Evaluate a compound trigger with AND/OR logic."""
    operator = config.get("operator", "AND").upper()
    sub_triggers = config.get("triggers", [])
    
    if not sub_triggers:
        return False, {}
    
    results = []
    trigger_data = {"sub_triggers": []}
    
    for sub_trigger in sub_triggers:
        triggered, data = await evaluate_trigger(sub_trigger)
        results.append(triggered)
        trigger_data["sub_triggers"].append({
            "trigger": sub_trigger,
            "triggered": triggered,
            "data": data,
        })
    
    if operator == "AND":
        final_triggered = all(results)
    elif operator == "OR":
        final_triggered = any(results)
    else:
        final_triggered = False
    
    trigger_data["operator"] = operator
    trigger_data["triggered"] = final_triggered
    
    return final_triggered, trigger_data


async def evaluate_trigger(trigger_def: Dict) -> Tuple[bool, Dict]:
    """
    Evaluate any trigger definition.
    
    Returns:
        (triggered: bool, data: Dict) - whether triggered and context data
    """
    trigger_type = trigger_def.get("type", "").lower()
    
    if trigger_type == "price":
        return await evaluate_price_trigger(trigger_def)
    
    elif trigger_type == "time":
        return await evaluate_time_trigger(trigger_def)
    
    elif trigger_type == "event":
        return await evaluate_event_trigger(trigger_def)
    
    elif trigger_type == "compound":
        return await evaluate_compound_trigger(trigger_def)
    
    elif trigger_type == "interval":
        # Alias for time trigger with interval
        return await evaluate_time_trigger(trigger_def)
    
    else:
        logger.warning(f"Unknown trigger type: {trigger_type}")
        return False, {}


# Pre-built trigger templates
TRIGGER_TEMPLATES = {
    "price_drop": {
        "type": "price",
        "asset": "SOL",
        "condition": "< 120",
    },
    "daily_morning": {
        "type": "time",
        "schedule": "at 09:00",
    },
    "every_hour": {
        "type": "time",
        "schedule": "every 1h",
    },
    "high_memory": {
        "type": "event",
        "event_type": "server_memory",
        "condition": "> 90",
    },
}


def get_trigger_template(name: str) -> Optional[Dict]:
    """Get a pre-built trigger template."""
    return TRIGGER_TEMPLATES.get(name)


def list_trigger_templates() -> Dict[str, Dict]:
    """List all available trigger templates."""
    return TRIGGER_TEMPLATES.copy()



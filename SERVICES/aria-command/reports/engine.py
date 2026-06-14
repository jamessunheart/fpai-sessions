#!/usr/bin/env python3
"""
Report Engine
=============
Main engine for generating and sending proactive reports.

This engine:
1. Gathers data from all sources
2. Generates appropriate reports
3. Delivers at the right time
4. Tracks what was sent
"""
import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List

from .templates import (
    ReportData,
    format_morning_brief, format_progress_report, format_status_report,
    format_heads_up, format_decision_request, format_digest,
    quick_status, quick_progress, quick_alert
)
from .scheduler import get_scheduler, ReportType
from .delivery import deliver_report, deliver_report_sync

logger = logging.getLogger("reports.engine")


class ReportEngine:
    """
    Main report generation engine.
    
    Responsibilities:
    - Gather data for reports
    - Generate formatted reports
    - Coordinate with scheduler and delivery
    """
    
    def __init__(self):
        self.scheduler = get_scheduler()
    
    # === Data Gathering ===
    
    def get_treasury_data(self) -> Dict:
        """Get trading/treasury data from Hyperliquid."""
        try:
            with open("/opt/fpai/hyperliquid_credentials.json") as f:
                creds = json.load(f)
            
            response = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": creds["main_account"]},
                timeout=5
            )
            
            state = response.json()
            margin = state.get("marginSummary", {})
            account_value = float(margin.get("accountValue", 0))
            
            # Get positions
            positions = []
            for p in state.get("assetPositions", []):
                pos = p.get("position", {})
                if float(pos.get("szi", 0)) != 0:
                    positions.append({
                        "symbol": pos.get("coin"),
                        "side": "LONG" if float(pos.get("szi", 0)) > 0 else "SHORT",
                        "size": abs(float(pos.get("szi", 0))),
                        "pnl": float(pos.get("unrealizedPnl", 0))
                    })
            
            return {
                "value": account_value,
                "positions": positions
            }
            
        except Exception as e:
            logger.error(f"Treasury data error: {e}")
            return {"value": None, "positions": []}
    
    def get_activity_data(self) -> Dict:
        """Get activity data from presence engine."""
        try:
            from presence import get_presence_engine
            engine = get_presence_engine()
            
            activities = engine.get_activities_today()
            queue = engine.get_queue()
            
            return {
                "count": len(activities),
                "activities": [
                    {"type": a.activity_type, "description": a.description}
                    for a in activities[:5]
                ],
                "queued": len(queue),
                "queue_items": queue[:3]
            }
            
        except Exception as e:
            logger.error(f"Activity data error: {e}")
            return {"count": 0, "activities": [], "queued": 0, "queue_items": []}
    
    def build_report_data(self) -> ReportData:
        """Build comprehensive report data."""
        treasury = self.get_treasury_data()
        activity = self.get_activity_data()
        
        return ReportData(
            treasury_value=treasury.get("value"),
            treasury_change=None,  # TODO: Calculate from history
            open_positions=treasury.get("positions"),
            activities_today=activity.get("count", 0),
            activities_list=activity.get("activities"),
            queued_items=activity.get("queued", 0),
            priority_items=activity.get("queue_items")
        )
    
    # === Report Generation ===
    
    def generate_morning_brief(self) -> str:
        """Generate morning brief report."""
        data = self.build_report_data()
        return format_morning_brief(data)
    
    def generate_status(self) -> str:
        """Generate status report."""
        data = self.build_report_data()
        return format_status_report(data)
    
    def generate_digest(self) -> str:
        """Generate daily digest."""
        data = self.build_report_data()
        return format_digest(data)
    
    def generate_progress(self, task: str, outcome: str = "completed", details: str = "") -> str:
        """Generate progress report."""
        return format_progress_report(task, outcome, details)
    
    def generate_heads_up(self, event: Dict) -> str:
        """Generate heads up for upcoming event."""
        return format_heads_up(event)
    
    def generate_decision(self, question: str, options: List[str] = None, context: str = "") -> str:
        """Generate decision request."""
        return format_decision_request(question, options, context)
    
    # === Sending Reports ===
    
    async def send_morning_brief(self) -> bool:
        """Send morning brief if appropriate."""
        if not self.scheduler.should_send_morning_brief():
            return False
        
        report = self.generate_morning_brief()
        return await deliver_report(report, "morning_brief", priority=2)
    
    async def send_status(self) -> bool:
        """Send status update if appropriate."""
        if not self.scheduler.should_send_status():
            return False
        
        report = self.generate_status()
        return await deliver_report(report, "status", priority=3)
    
    async def send_digest(self) -> bool:
        """Send daily digest if appropriate."""
        if not self.scheduler.should_send_digest():
            return False
        
        report = self.generate_digest()
        return await deliver_report(report, "digest", priority=2)
    
    async def send_progress(self, task: str, outcome: str = "completed", details: str = "") -> bool:
        """Send progress report."""
        report = self.generate_progress(task, outcome, details)
        return await deliver_report(report, "progress", priority=3)
    
    async def send_heads_up(self, event: Dict) -> bool:
        """Send heads up for event."""
        report = self.generate_heads_up(event)
        return await deliver_report(report, "heads_up", priority=2)
    
    async def send_decision(self, question: str, options: List[str] = None, context: str = "") -> bool:
        """Send decision request."""
        report = self.generate_decision(question, options, context)
        return await deliver_report(report, "decision", priority=1)
    
    async def send_quick(self, message: str, report_type: str = "status") -> bool:
        """Send a quick message."""
        if report_type == "progress":
            formatted = quick_progress(message)
        elif report_type == "alert":
            formatted = quick_alert(message)
        else:
            formatted = quick_status(message)
        
        return await deliver_report(formatted, report_type, priority=3)
    
    # === Proactive Loop ===
    
    async def check_and_send_scheduled(self) -> List[str]:
        """Check if any scheduled reports should be sent now."""
        sent = []
        
        if await self.send_morning_brief():
            sent.append("morning_brief")
        
        if await self.send_status():
            sent.append("status")
        
        if await self.send_digest():
            sent.append("digest")
        
        return sent


# Singleton
_engine: Optional[ReportEngine] = None

def get_report_engine() -> ReportEngine:
    global _engine
    if _engine is None:
        _engine = ReportEngine()
    return _engine


# Convenience functions

async def send_morning_brief() -> bool:
    return await get_report_engine().send_morning_brief()

async def send_status() -> bool:
    return await get_report_engine().send_status()

async def send_digest() -> bool:
    return await get_report_engine().send_digest()

async def send_progress(task: str, outcome: str = "completed", details: str = "") -> bool:
    return await get_report_engine().send_progress(task, outcome, details)

async def send_quick(message: str, report_type: str = "status") -> bool:
    return await get_report_engine().send_quick(message, report_type)

async def check_scheduled_reports() -> List[str]:
    return await get_report_engine().check_and_send_scheduled()









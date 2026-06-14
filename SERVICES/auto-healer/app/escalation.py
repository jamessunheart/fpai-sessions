"""
Escalation - Alert management when auto-healing fails
"""
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

from .config import (
    ALERT_EMAIL, 
    COMMUNICATION_HUB_URL, 
    GOD_MODE_URL,
    MAX_AUTO_RESTARTS,
    CRITICAL_DOWN_THRESHOLD,
    RECURRING_FAILURE_THRESHOLD,
)
from .healing_executor import HealingOutcome, HealingResult
from .failure_analyzer import FailureDiagnosis
from .knowledge_base import knowledge_base

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An alert to be sent."""
    service_name: str
    severity: AlertSeverity
    title: str
    message: str
    suggested_action: Optional[str] = None
    diagnosis: Optional[FailureDiagnosis] = None
    outcome: Optional[HealingOutcome] = None
    timestamp: datetime = field(default_factory=datetime.now)
    sent: bool = False
    channels_sent: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "timestamp": self.timestamp.isoformat(),
            "sent": self.sent,
            "channels_sent": self.channels_sent,
        }


class EscalationManager:
    """
    Manages alerting when auto-healing fails or human intervention is needed.
    """
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.service_down_since: Dict[str, datetime] = {}
        self.suppressed_until: Dict[str, datetime] = {}
    
    def should_escalate(self, service_name: str, outcome: HealingOutcome) -> tuple[bool, str]:
        """
        Determine if an escalation is needed based on the healing outcome.
        Returns: (should_escalate, reason)
        """
        # Check if alerts are suppressed for this service
        if service_name in self.suppressed_until:
            if datetime.now() < self.suppressed_until[service_name]:
                return False, "Alerts suppressed"
        
        # Max attempts reached
        if outcome.result == HealingResult.FAILED:
            recent_outcomes = knowledge_base.get_recent_outcomes(limit=MAX_AUTO_RESTARTS, service_name=service_name)
            recent_failures = sum(1 for o in recent_outcomes if o['result'] == 'failed')
            if recent_failures >= MAX_AUTO_RESTARTS:
                return True, f"Max healing attempts ({MAX_AUTO_RESTARTS}) reached"
        
        # Requires human intervention
        if outcome.result == HealingResult.REQUIRES_HUMAN:
            return True, "Requires human intervention"
        
        return False, "No escalation needed"
    
    def check_critical_down_time(self, service_name: str, is_critical: bool, is_healthy: bool) -> Optional[Alert]:
        """
        Check if a critical service has been down too long.
        """
        if is_healthy:
            # Service recovered, clear tracking
            if service_name in self.service_down_since:
                del self.service_down_since[service_name]
            return None
        
        if not is_critical:
            return None
        
        # Track when service went down
        if service_name not in self.service_down_since:
            self.service_down_since[service_name] = datetime.now()
            return None
        
        # Check if down too long
        down_time = (datetime.now() - self.service_down_since[service_name]).total_seconds()
        if down_time >= CRITICAL_DOWN_THRESHOLD:
            return Alert(
                service_name=service_name,
                severity=AlertSeverity.CRITICAL,
                title=f"CRITICAL: {service_name} down for {int(down_time/60)} minutes",
                message=f"Critical service {service_name} has been down for {int(down_time)} seconds. "
                        f"Auto-healing has not been able to restore it.",
                suggested_action="Manual intervention required - SSH to server and check logs",
            )
        
        return None
    
    def check_recurring_pattern(self, service_name: str, failure_type: str) -> Optional[Alert]:
        """
        Check for recurring failure patterns that need human attention.
        """
        patterns = knowledge_base.get_recurring_patterns(flagged_only=True)
        
        for pattern in patterns:
            if pattern['service_name'] == service_name and pattern['failure_type'] == failure_type:
                return Alert(
                    service_name=service_name,
                    severity=AlertSeverity.WARNING,
                    title=f"Recurring failure: {service_name} - {failure_type}",
                    message=f"Service {service_name} has experienced {pattern['occurrence_count']} "
                            f"'{failure_type}' failures in the last 24 hours. "
                            f"This indicates a persistent issue that needs a permanent fix.",
                    suggested_action=f"Review and fix root cause of {failure_type} failures",
                )
        
        return None
    
    def create_alert(
        self, 
        service_name: str, 
        outcome: HealingOutcome, 
        diagnosis: Optional[FailureDiagnosis] = None
    ) -> Alert:
        """
        Create an alert for a failed healing attempt.
        """
        if outcome.result == HealingResult.REQUIRES_HUMAN:
            severity = AlertSeverity.WARNING
            title = f"Human intervention needed: {service_name}"
        else:
            severity = AlertSeverity.CRITICAL
            title = f"Auto-heal failed: {service_name}"
        
        message_parts = [
            f"Service: {service_name}",
            f"Failure type: {outcome.failure_type.value}",
            f"Action attempted: {outcome.action_name}",
            f"Result: {outcome.result.value}",
        ]
        
        if outcome.error:
            message_parts.append(f"Error: {outcome.error}")
        
        if diagnosis and diagnosis.evidence:
            message_parts.append(f"Evidence: {diagnosis.evidence[:200]}")
        
        suggested_action = None
        if diagnosis and diagnosis.suggested_fix:
            suggested_action = diagnosis.suggested_fix
        elif outcome.notes:
            suggested_action = outcome.notes
        
        return Alert(
            service_name=service_name,
            severity=severity,
            title=title,
            message="\n".join(message_parts),
            suggested_action=suggested_action,
            diagnosis=diagnosis,
            outcome=outcome,
        )
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send alert through available channels.
        """
        success = False
        
        # Try Communication Hub (email)
        try:
            email_sent = await self._send_via_communication_hub(alert)
            if email_sent:
                alert.channels_sent.append("email")
                success = True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
        
        # Try God Mode notification
        try:
            godmode_sent = await self._send_to_god_mode(alert)
            if godmode_sent:
                alert.channels_sent.append("god_mode")
                success = True
        except Exception as e:
            logger.error(f"Failed to send God Mode notification: {e}")
        
        alert.sent = success
        self.alerts.append(alert)
        
        if success:
            logger.info(f"Alert sent for {alert.service_name}: {alert.title}")
        else:
            logger.warning(f"Alert could not be sent for {alert.service_name}")
        
        return success
    
    async def _send_via_communication_hub(self, alert: Alert) -> bool:
        """Send alert via Communication Hub (email)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{COMMUNICATION_HUB_URL}/api/v1/send",
                    json={
                        "channel": "email",
                        "recipient": ALERT_EMAIL,
                        "subject": f"🚨 [{alert.severity.value.upper()}] {alert.title}",
                        "content": self._format_email_content(alert),
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Communication Hub unavailable: {e}")
            return False
    
    async def _send_to_god_mode(self, alert: Alert) -> bool:
        """Send notification to God Mode dashboard."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{GOD_MODE_URL}/api/notifications",
                    json={
                        "type": "auto_healer_alert",
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "service": alert.service_name,
                        "suggested_action": alert.suggested_action,
                        "timestamp": alert.timestamp.isoformat(),
                    }
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"God Mode notification failed: {e}")
            return False
    
    def _format_email_content(self, alert: Alert) -> str:
        """Format alert for email."""
        content = f"""
Auto-Healer Alert
=================

{alert.title}

Details:
{alert.message}

{"Suggested Action:" if alert.suggested_action else ""}
{alert.suggested_action or ""}

Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

---
This alert was generated by the FPAI Auto-Healer system.
Dashboard: https://fullpotential.ai/dashboards/team?view=god
"""
        return content.strip()
    
    def suppress_alerts(self, service_name: str, duration_minutes: int = 60):
        """Suppress alerts for a service temporarily."""
        self.suppressed_until[service_name] = datetime.now() + timedelta(minutes=duration_minutes)
        logger.info(f"Alerts suppressed for {service_name} for {duration_minutes} minutes")
    
    def unsuppress_alerts(self, service_name: str):
        """Remove alert suppression for a service."""
        if service_name in self.suppressed_until:
            del self.suppressed_until[service_name]
            logger.info(f"Alerts unsuppressed for {service_name}")
    
    def get_recent_alerts(self, limit: int = 50) -> List[dict]:
        """Get recent alerts."""
        return [a.to_dict() for a in self.alerts[-limit:]]
    
    def get_suppressed_services(self) -> Dict[str, str]:
        """Get currently suppressed services."""
        now = datetime.now()
        return {
            name: until.isoformat()
            for name, until in self.suppressed_until.items()
            if until > now
        }


# Global escalation manager instance
escalation_manager = EscalationManager()












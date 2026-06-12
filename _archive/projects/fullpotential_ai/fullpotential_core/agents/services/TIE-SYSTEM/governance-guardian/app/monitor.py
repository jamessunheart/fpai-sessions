"""
Core governance monitoring engine
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import httpx

from .database import async_session_maker
from . import crud
from .models import (
    GuardianStatusResponse,
    GovernanceMetricsResponse,
    SystemRulesResponse
)

logger = logging.getLogger(__name__)


class GovernanceMonitor:
    """
    Core monitoring engine for TIE governance.

    Continuously polls voting-weight-tracker and enforces
    holder control requirements.
    """

    def __init__(self):
        # Configuration
        self.voting_tracker_url = os.getenv(
            "VOTING_TRACKER_URL",
            "http://localhost:8922"
        )
        self.redemption_algorithm_url = os.getenv(
            "REDEMPTION_ALGORITHM_URL",
            "http://localhost:8923"
        )

        # Thresholds
        self.critical_threshold = float(os.getenv("CRITICAL_THRESHOLD", "51.0"))
        self.warning_threshold = float(os.getenv("WARNING_THRESHOLD", "52.0"))
        self.caution_threshold = float(os.getenv("CAUTION_THRESHOLD", "55.0"))
        self.pause_redemptions_at = float(os.getenv("PAUSE_REDEMPTIONS_AT", "51.0"))
        self.pause_system_at = float(os.getenv("PAUSE_SYSTEM_AT", "49.0"))

        # Monitoring intervals (seconds)
        self.interval_normal = int(os.getenv("MONITORING_INTERVAL_NORMAL", "30"))
        self.interval_caution = int(os.getenv("MONITORING_INTERVAL_CAUTION", "5"))
        self.interval_critical = int(os.getenv("MONITORING_INTERVAL_CRITICAL", "1"))

        # State
        self.monitoring_active = False
        self.last_check: Optional[datetime] = None
        self.current_holder_control: float = 0.0
        self.current_threshold_level: str = "unknown"
        self.system_status: str = "operational"
        self.paused: bool = False
        self.check_interval: int = self.interval_normal

    async def start_monitoring(self):
        """Start the governance monitoring loop."""
        self.monitoring_active = True
        logger.info("🛡️  Governance monitoring started")

        while self.monitoring_active:
            try:
                await self._monitoring_cycle()
            except Exception as e:
                logger.error(f"Monitoring cycle error: {e}")
                await asyncio.sleep(30)  # Retry in 30 seconds on error

    async def stop_monitoring(self):
        """Stop the governance monitoring loop."""
        self.monitoring_active = False
        logger.info("🛡️  Governance monitoring stopped")

    async def _monitoring_cycle(self):
        """Single monitoring cycle."""
        try:
            # 1. Fetch governance status from voting-weight-tracker
            governance = await self._fetch_governance_status()

            if governance:
                self.last_check = datetime.utcnow()
                self.current_holder_control = governance["holder_control_percentage"]

                # 2. Determine threshold level
                threshold_level = self._determine_threshold_level(self.current_holder_control)
                self.current_threshold_level = threshold_level

                # 3. Log governance check event
                async with async_session_maker() as db:
                    await crud.log_governance_event(
                        db=db,
                        event_type="governance_check",
                        holder_control=self.current_holder_control,
                        threshold_level=threshold_level,
                        action="none",
                        details=f"Routine check: {self.current_holder_control}%"
                    )
                    await db.commit()

                # 4. Check for threshold violations
                await self._check_thresholds(governance)

                # 5. Adjust monitoring interval
                self.check_interval = self._get_monitoring_interval(threshold_level)

            else:
                logger.error("Failed to fetch governance status")
                self.check_interval = 30  # Default retry interval

            # 6. Wait for next check
            await asyncio.sleep(self.check_interval)

        except Exception as e:
            logger.error(f"Monitoring cycle error: {e}")
            await asyncio.sleep(30)

    async def _fetch_governance_status(self) -> Optional[dict]:
        """Fetch current governance status from voting-weight-tracker."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.voting_tracker_url}/voting/governance")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch governance status: {e}")
            return None

    def _determine_threshold_level(self, holder_control: float) -> str:
        """Determine threshold level based on holder control percentage."""
        if holder_control >= 70.0:
            return "excellent"
        elif holder_control >= 60.0:
            return "good"
        elif holder_control >= 55.0:
            return "acceptable"
        elif holder_control >= 51.0:
            return "caution"
        elif holder_control >= 49.0:
            return "warning"
        else:
            return "critical"

    def _get_monitoring_interval(self, threshold_level: str) -> int:
        """Get monitoring interval based on threshold level."""
        if threshold_level in ["critical", "warning"]:
            return self.interval_critical
        elif threshold_level == "caution":
            return self.interval_caution
        else:
            return self.interval_normal

    async def _check_thresholds(self, governance: dict):
        """Check for threshold violations and take appropriate action."""
        holder_control = governance["holder_control_percentage"]

        async with async_session_maker() as db:
            try:
                # Critical: <49% - Full system pause
                if holder_control < self.pause_system_at:
                    await self._handle_critical_emergency(db, holder_control)

                # Critical: <51% - Pause redemptions
                elif holder_control < self.critical_threshold:
                    await self._handle_critical_threshold(db, holder_control)

                # Warning: <52% - Urgent alert
                elif holder_control < self.warning_threshold:
                    await self._handle_warning_threshold(db, holder_control)

                # Caution: <55% - Alert
                elif holder_control < self.caution_threshold:
                    await self._handle_caution_threshold(db, holder_control)

                # Safe: >=55% - Clear alerts if needed
                else:
                    await self._clear_alerts_if_safe(db, holder_control)

                await db.commit()

            except Exception as e:
                logger.error(f"Threshold check error: {e}")
                await db.rollback()

    async def _handle_caution_threshold(self, db, holder_control: float):
        """Handle caution threshold (holder control <55%)."""
        # Check if we already have an active caution alert
        active_alerts = await crud.get_active_alerts_count(db)

        if active_alerts == 0:
            # Create caution alert
            await crud.create_alert(
                db=db,
                alert_type="caution",
                holder_control=holder_control,
                message=f"Holder control at {holder_control}% (below 55%)",
                action_taken="increased_monitoring"
            )

            # Log event
            await crud.log_governance_event(
                db=db,
                event_type="threshold_crossed",
                holder_control=holder_control,
                threshold_level="caution",
                action="alert",
                details="Holder control below 55% - increased monitoring to 5 seconds"
            )

            logger.warning(f"⚠️  CAUTION: Holder control at {holder_control}% (below 55%)")

    async def _handle_warning_threshold(self, db, holder_control: float):
        """Handle warning threshold (holder control <52%)."""
        # Create warning alert
        await crud.create_alert(
            db=db,
            alert_type="warning",
            holder_control=holder_control,
            message=f"URGENT: Holder control at {holder_control}% (below 52%)",
            action_taken="critical_monitoring"
        )

        # Log event
        await crud.log_governance_event(
            db=db,
            event_type="threshold_crossed",
            holder_control=holder_control,
            threshold_level="warning",
            action="alert",
            details="Holder control below 52% - critical monitoring every 1 second"
        )

        logger.error(f"🚨 WARNING: Holder control at {holder_control}% (below 52%)")

        # TODO: Send urgent notifications (Slack, email)

    async def _handle_critical_threshold(self, db, holder_control: float):
        """Handle critical threshold (holder control <51%)."""
        # Check if already paused
        current_pause = await crud.get_current_pause(db)

        if not current_pause:
            # Create critical alert
            await crud.create_alert(
                db=db,
                alert_type="critical",
                holder_control=holder_control,
                message=f"CRITICAL: Holder control at {holder_control}% (below 51%)",
                action_taken="paused_redemptions"
            )

            # Create pause record
            await crud.create_pause_record(
                db=db,
                pause_reason=f"Automatic pause: Holder control at {holder_control}% (below 51%)",
                pause_type="automatic",
                holder_control=holder_control
            )

            # Log event
            await crud.log_governance_event(
                db=db,
                event_type="pause",
                holder_control=holder_control,
                threshold_level="critical",
                action="pause",
                details="System paused - holder control below 51%"
            )

            # Update state
            self.system_status = "redemptions_paused"
            self.paused = True

            logger.error(f"🚨 CRITICAL: System paused - holder control at {holder_control}%")

            # TODO: Pause redemption-algorithm
            # await self._pause_redemptions()

            # TODO: Send emergency notifications

    async def _handle_critical_emergency(self, db, holder_control: float):
        """Handle emergency threshold (holder control <49%)."""
        # Create emergency alert
        await crud.create_alert(
            db=db,
            alert_type="emergency",
            holder_control=holder_control,
            message=f"EMERGENCY: Holder control at {holder_control}% (below 49%)",
            action_taken="full_system_pause"
        )

        # Create pause record if not already paused
        current_pause = await crud.get_current_pause(db)
        if not current_pause:
            await crud.create_pause_record(
                db=db,
                pause_reason=f"EMERGENCY: Holder control at {holder_control}% (below 49%)",
                pause_type="automatic",
                holder_control=holder_control
            )

        # Log event
        await crud.log_governance_event(
            db=db,
            event_type="pause",
            holder_control=holder_control,
            threshold_level="critical",
            action="pause",
            details="FULL SYSTEM PAUSE - holder control below 49%"
        )

        # Update state
        self.system_status = "fully_paused"
        self.paused = True

        logger.error(f"🚨🚨🚨 EMERGENCY: Full system pause - holder control at {holder_control}%")

        # TODO: Pause all services
        # TODO: Send emergency alerts to all administrators

    async def _clear_alerts_if_safe(self, db, holder_control: float):
        """Clear alerts if holder control is back in safe range."""
        # Get active alerts
        active_alerts = await crud.get_alerts(db, limit=100, resolved=False)

        if active_alerts:
            # Resolve all active alerts
            for alert in active_alerts:
                await crud.resolve_alert(db, alert.id)

            # Log recovery
            await crud.log_governance_event(
                db=db,
                event_type="threshold_crossed",
                holder_control=holder_control,
                threshold_level="acceptable",
                action="none",
                details=f"Holder control restored to {holder_control}% - alerts cleared"
            )

            logger.info(f"✅ Holder control restored to {holder_control}% - alerts cleared")

    async def get_status(self) -> GuardianStatusResponse:
        """Get current guardian status."""
        async with async_session_maker() as db:
            alerts_active = await crud.get_active_alerts_count(db)

        return GuardianStatusResponse(
            monitoring_active=self.monitoring_active,
            last_check=self.last_check,
            check_interval_seconds=self.check_interval,
            current_holder_control=self.current_holder_control,
            governance_level=self.current_threshold_level,
            system_status=self.system_status,
            paused=self.paused,
            alerts_active=alerts_active
        )

    async def get_current_governance(self) -> GovernanceMetricsResponse:
        """Get current governance metrics from voting-weight-tracker."""
        governance = await self._fetch_governance_status()

        if not governance:
            raise Exception("Failed to fetch governance status")

        threshold_level = self._determine_threshold_level(governance["holder_control_percentage"])

        return GovernanceMetricsResponse(
            holder_control_percentage=governance["holder_control_percentage"],
            total_votes=governance["total_votes"],
            holder_votes=governance["holder_votes"],
            seller_votes=governance["seller_votes"],
            threshold_level=threshold_level,
            margin_above_critical=governance["margin_above_critical"],
            is_stable=governance["is_stable"],
            last_updated=datetime.utcnow()
        )

    async def get_current_holder_control(self) -> float:
        """Get current holder control percentage."""
        governance = await self._fetch_governance_status()
        return governance["holder_control_percentage"] if governance else 0.0

    async def pause_system(self, db, reason: str, pause_type: str, holder_control: float):
        """Manually pause the system."""
        pause_record = await crud.create_pause_record(
            db=db,
            pause_reason=reason,
            pause_type=pause_type,
            holder_control=holder_control
        )

        await crud.log_governance_event(
            db=db,
            event_type="pause",
            holder_control=holder_control,
            threshold_level=self.current_threshold_level,
            action="pause",
            details=f"Manual pause: {reason}"
        )

        self.system_status = "fully_paused"
        self.paused = True

        await db.commit()
        return pause_record

    async def resume_system(self, db, resumed_by: str):
        """Resume system operations."""
        pause_record = await crud.resume_pause_record(
            db=db,
            resumed_by=resumed_by,
            resume_reason="Manual resume - governance verified"
        )

        await crud.log_governance_event(
            db=db,
            event_type="resume",
            holder_control=self.current_holder_control,
            threshold_level=self.current_threshold_level,
            action="resume",
            details=f"System resumed by {resumed_by}"
        )

        self.system_status = "operational"
        self.paused = False

        await db.commit()
        return pause_record

    def get_rules(self) -> SystemRulesResponse:
        """Get current system rules and thresholds."""
        return SystemRulesResponse(
            critical_threshold=self.critical_threshold,
            warning_threshold=self.warning_threshold,
            caution_threshold=self.caution_threshold,
            pause_redemptions_at=self.pause_redemptions_at,
            pause_system_at=self.pause_system_at,
            monitoring_interval_normal=self.interval_normal,
            monitoring_interval_caution=self.interval_caution,
            monitoring_interval_critical=self.interval_critical
        )

    async def check_voting_tracker_connection(self) -> bool:
        """Check if voting-weight-tracker is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.voting_tracker_url}/health")
                return response.status_code == 200
        except Exception:
            return False

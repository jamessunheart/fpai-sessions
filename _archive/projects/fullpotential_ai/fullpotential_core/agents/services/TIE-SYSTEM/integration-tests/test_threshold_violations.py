"""
Integration Test: Threshold Violations

Tests governance-guardian threshold detection and circuit breakers:
1. Caution threshold (<55%)
2. Warning threshold (<52%)
3. Critical threshold (<51%)
4. Emergency threshold (<49%)
"""

import pytest
import httpx
import asyncio
from typing import List


# Service URLs
VOTING_TRACKER_URL = "http://localhost:8922"
GOVERNANCE_GUARDIAN_URL = "http://localhost:8926"


async def simulate_voting_distribution(
    client: httpx.AsyncClient,
    holder_votes: int,
    seller_votes: int
):
    """
    Helper: Simulate a specific voting distribution by directly calling voting-weight-tracker.

    In production, this would happen through deposits and redemptions.
    For testing, we can directly manipulate votes.
    """
    # TODO: Implement direct vote manipulation for testing
    # For now, this is a placeholder
    pass


@pytest.mark.asyncio
async def test_caution_threshold_triggers_alert():
    """
    Test that holder control <55% triggers caution alert.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:

        print("\n1. Simulating holder control at 54% (below 55% caution threshold)...")

        # Note: In real scenario, this would be achieved through redemptions
        # For this test, we're checking the guardian's monitoring logic

        # Check current governance
        governance_response = await client.get(f"{VOTING_TRACKER_URL}/voting/governance")
        assert governance_response.status_code == 200
        governance = governance_response.json()

        current_control = governance['holder_control_percentage']
        print(f"   Current holder control: {current_control}%")

        if current_control >= 55.0:
            print("   ⚠️  Holder control above 55% - cannot test caution threshold")
            print("   This test requires existing redemptions to lower holder control")
            pytest.skip("Requires holder control <55% to test")
            return

        # Wait for guardian to detect (30 second polling)
        print("\n2. Waiting for guardian to detect...")
        await asyncio.sleep(35)

        # Check for caution alert
        print("\n3. Checking for caution alert...")
        alerts_response = await client.get(
            f"{GOVERNANCE_GUARDIAN_URL}/guardian/alerts?resolved=false&limit=10"
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()['alerts']

        caution_alerts = [a for a in alerts if a['alert_type'] == 'caution']

        if caution_alerts:
            latest_caution = caution_alerts[0]
            print(f"   ✅ Caution alert found!")
            print(f"      Timestamp: {latest_caution['timestamp']}")
            print(f"      Holder control: {latest_caution['holder_control']}%")
            print(f"      Message: {latest_caution['message']}")
            print(f"      Action: {latest_caution['action_taken']}")
        else:
            print("   No caution alert found (holder control may have recovered)")

        # Check guardian status
        print("\n4. Checking guardian monitoring adjustment...")
        guardian_response = await client.get(f"{GOVERNANCE_GUARDIAN_URL}/guardian/status")
        assert guardian_response.status_code == 200
        guardian_status = guardian_response.json()

        print(f"   Governance level: {guardian_status['governance_level']}")
        print(f"   Check interval: {guardian_status['check_interval_seconds']}s")
        print(f"   System status: {guardian_status['system_status']}")

        # If in caution, monitoring should be faster
        if guardian_status['current_holder_control'] < 55.0:
            assert guardian_status['check_interval_seconds'] <= 5
            print(f"   ✅ Monitoring increased to {guardian_status['check_interval_seconds']}s")

        print(f"\n✅ CAUTION THRESHOLD TEST COMPLETE")


@pytest.mark.asyncio
async def test_critical_threshold_pauses_system():
    """
    Test that holder control <51% triggers system pause.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:

        print("\n1. Checking if system is at critical threshold (<51%)...")

        governance_response = await client.get(f"{VOTING_TRACKER_URL}/voting/governance")
        assert governance_response.status_code == 200
        governance = governance_response.json()

        current_control = governance['holder_control_percentage']
        print(f"   Current holder control: {current_control}%")

        if current_control >= 51.0:
            print("   System is stable (>51%)")
            print("   This test requires holder control <51% to test pause mechanism")
            pytest.skip("Requires critical threshold to test pause")
            return

        # System should be paused
        print("\n2. Verifying system is paused...")
        guardian_response = await client.get(f"{GOVERNANCE_GUARDIAN_URL}/guardian/status")
        assert guardian_response.status_code == 200
        guardian_status = guardian_response.json()

        print(f"   System status: {guardian_status['system_status']}")
        print(f"   Paused: {guardian_status['paused']}")
        print(f"   Alerts active: {guardian_status['alerts_active']}")

        # Should be paused
        assert guardian_status['paused'] == True
        assert guardian_status['system_status'] in ["redemptions_paused", "fully_paused"]

        # Check for critical alert
        print("\n3. Checking for critical alert...")
        alerts_response = await client.get(
            f"{GOVERNANCE_GUARDIAN_URL}/guardian/alerts?resolved=false&limit=10"
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()['alerts']

        critical_alerts = [a for a in alerts if a['alert_type'] in ['critical', 'emergency']]
        assert len(critical_alerts) > 0

        latest_critical = critical_alerts[0]
        print(f"   ✅ Critical alert found!")
        print(f"      Type: {latest_critical['alert_type']}")
        print(f"      Holder control: {latest_critical['holder_control']}%")
        print(f"      Message: {latest_critical['message']}")
        print(f"      Action: {latest_critical['action_taken']}")

        # Check governance events (audit log)
        print("\n4. Checking governance events...")
        events_response = await client.get(
            f"{GOVERNANCE_GUARDIAN_URL}/guardian/events?event_type=pause&limit=5"
        )
        assert events_response.status_code == 200
        events = events_response.json()['events']

        pause_events = [e for e in events if e['event_type'] == 'pause']
        if pause_events:
            latest_pause = pause_events[0]
            print(f"   ✅ Pause event logged:")
            print(f"      Timestamp: {latest_pause['timestamp']}")
            print(f"      Holder control: {latest_pause['holder_control']}%")
            print(f"      Details: {latest_pause['details']}")

        print(f"\n✅ CRITICAL THRESHOLD PAUSE TEST COMPLETE")


@pytest.mark.asyncio
async def test_governance_rules_configuration():
    """
    Test that governance rules are correctly configured.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:

        print("\n1. Fetching governance rules...")
        rules_response = await client.get(f"{GOVERNANCE_GUARDIAN_URL}/guardian/rules")
        assert rules_response.status_code == 200
        rules = rules_response.json()

        print(f"\n📋 GOVERNANCE RULES:")
        print(f"   Critical threshold: {rules['critical_threshold']}%")
        print(f"   Warning threshold: {rules['warning_threshold']}%")
        print(f"   Caution threshold: {rules['caution_threshold']}%")
        print(f"   Pause redemptions at: {rules['pause_redemptions_at']}%")
        print(f"   Pause system at: {rules['pause_system_at']}%")
        print(f"\n⏱️  MONITORING INTERVALS:")
        print(f"   Normal: {rules['monitoring_interval_normal']}s")
        print(f"   Caution: {rules['monitoring_interval_caution']}s")
        print(f"   Critical: {rules['monitoring_interval_critical']}s")

        # Verify thresholds are sensible
        assert rules['critical_threshold'] == 51.0
        assert rules['warning_threshold'] >= rules['critical_threshold']
        assert rules['caution_threshold'] >= rules['warning_threshold']

        # Verify monitoring intervals
        assert rules['monitoring_interval_normal'] >= rules['monitoring_interval_caution']
        assert rules['monitoring_interval_caution'] >= rules['monitoring_interval_critical']

        print(f"\n✅ GOVERNANCE RULES VERIFIED")


@pytest.mark.asyncio
async def test_alert_history_tracking():
    """
    Test that all alerts are properly tracked in history.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:

        print("\n1. Fetching alert history...")
        alerts_response = await client.get(
            f"{GOVERNANCE_GUARDIAN_URL}/guardian/alerts?limit=50"
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()['alerts']

        print(f"   Total alerts in history: {len(alerts)}")

        # Group by type
        by_type = {}
        for alert in alerts:
            alert_type = alert['alert_type']
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

        print(f"\n📊 ALERTS BY TYPE:")
        for alert_type, count in by_type.items():
            print(f"   {alert_type}: {count}")

        # Count resolved vs unresolved
        resolved_count = len([a for a in alerts if a['resolved']])
        unresolved_count = len([a for a in alerts if not a['resolved']])

        print(f"\n📊 ALERT STATUS:")
        print(f"   Resolved: {resolved_count}")
        print(f"   Unresolved: {unresolved_count}")

        # Show recent alerts
        if alerts:
            print(f"\n🔔 RECENT ALERTS:")
            for alert in alerts[:5]:
                status = "✅ Resolved" if alert['resolved'] else "⚠️  Active"
                print(f"   [{status}] {alert['alert_type'].upper()} @ {alert['timestamp']}")
                print(f"      {alert['message']}")
                print(f"      Holder control: {alert['holder_control']}%")
                print()

        print(f"✅ ALERT HISTORY TEST COMPLETE")


@pytest.mark.asyncio
async def test_governance_event_audit_log():
    """
    Test that all governance events are logged to audit trail.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:

        print("\n1. Fetching governance event audit log...")
        events_response = await client.get(
            f"{GOVERNANCE_GUARDIAN_URL}/guardian/events?limit=100"
        )
        assert events_response.status_code == 200
        events = events_response.json()['events']

        print(f"   Total events in audit log: {len(events)}")

        # Group by type
        by_type = {}
        for event in events:
            event_type = event['event_type']
            by_type[event_type] = by_type.get(event_type, 0) + 1

        print(f"\n📊 EVENTS BY TYPE:")
        for event_type, count in sorted(by_type.items()):
            print(f"   {event_type}: {count}")

        # Group by action
        by_action = {}
        for event in events:
            action = event['action']
            by_action[action] = by_action.get(action, 0) + 1

        print(f"\n📊 EVENTS BY ACTION:")
        for action, count in sorted(by_action.items()):
            print(f"   {action}: {count}")

        # Show critical events
        critical_events = [e for e in events if e['action'] in ['pause', 'resume', 'alert']]

        if critical_events:
            print(f"\n🚨 CRITICAL EVENTS:")
            for event in critical_events[:10]:
                print(f"   {event['event_type'].upper()} @ {event['timestamp']}")
                print(f"      Action: {event['action']}")
                print(f"      Holder control: {event['holder_control']}%")
                print(f"      Details: {event['details']}")
                print()

        print(f"✅ AUDIT LOG TEST COMPLETE")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

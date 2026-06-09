#!/usr/bin/env python3
"""Initialize governance rules on the bus and set up trackers."""
import json
import requests
from datetime import datetime, timezone

BUS = "http://127.0.0.1:8195"
now = datetime.now(timezone.utc).isoformat()

# Write all 5 governance rules to bus as permanent steering
rules = {
    "G1_revenue_accountability": {
        "rule": "Track days since last revenue event every cycle. After 7 days: revenue is top priority. After 14 days: block all new infrastructure builds.",
        "enforcement": "non-overridable",
        "suspend_authority": "Sunheart only"
    },
    "G2_activity_ratio": {
        "rule": "Every cycle evaluate infrastructure vs revenue-generating activity ratio. Target: 80% revenue / 20% infrastructure. Flag inversion as primary pattern alert.",
        "enforcement": "non-overridable",
        "suspend_authority": "Sunheart only"
    },
    "G3_ot_enforcement": {
        "rule": "Check if 3+ outbound touches executed today. If not, Directive 1 must be execute outbound touches. No exceptions.",
        "enforcement": "non-overridable",
        "suspend_authority": "Sunheart only"
    },
    "G4_zen_village_bleed": {
        "rule": "Zen Village idle cost increments $133/day with zero rental income. Surface running total every cycle.",
        "enforcement": "non-overridable",
        "suspend_authority": "Sunheart only"
    },
    "G5_builder_drift": {
        "rule": "If 3+ consecutive cycles are infrastructure-focused with no customer-facing output, name it explicitly and force-redirect to revenue.",
        "enforcement": "non-overridable",
        "suspend_authority": "Sunheart only"
    }
}

# Write governance rules
resp = requests.post(f"{BUS}/bus/messages", json={
    "from": "kai",
    "to": "cora",
    "type": "governance",
    "priority": "high",
    "content": {
        "title": "CORA Governance Rules G1-G5",
        "rules": rules,
        "effective_date": now,
        "authority": "Kai-Sunheart strategic session",
        "override_policy": "Only Sunheart can suspend via direct steering"
    }
})
print(f"Governance rules written to bus: {resp.json().get('id', 'error')[:12]}")

# Initialize trackers in bus
# Zen Village bleed tracker - starts today
resp = requests.post(f"{BUS}/bus/messages", json={
    "from": "kai",
    "to": "cora",
    "type": "tracker_init",
    "priority": "high",
    "content": {
        "tracker": "zen_village_bleed",
        "start_date": "2026-03-15",
        "daily_cost": 133,
        "current_total": 0,
        "description": "Zen Village idle cost — $133/day with zero rental income"
    }
})
print(f"Zen Village bleed tracker initialized: {resp.json().get('id', 'error')[:12]}")

# Revenue event tracker - last known event is unknown, start counting from today
resp = requests.post(f"{BUS}/bus/messages", json={
    "from": "kai",
    "to": "cora",
    "type": "tracker_init",
    "priority": "high",
    "content": {
        "tracker": "revenue_events",
        "last_revenue_event": None,
        "days_since_last": "unknown — no revenue event recorded yet",
        "description": "Days since last payment received or call booked"
    }
})
print(f"Revenue event tracker initialized: {resp.json().get('id', 'error')[:12]}")

# Builder drift counter
resp = requests.post(f"{BUS}/bus/messages", json={
    "from": "kai",
    "to": "cora",
    "type": "tracker_init",
    "priority": "medium",
    "content": {
        "tracker": "builder_drift",
        "consecutive_infra_cycles": 4,
        "last_customer_facing_output": None,
        "description": "Consecutive cycles spent primarily on infrastructure"
    }
})
print(f"Builder drift tracker initialized: {resp.json().get('id', 'error')[:12]}")

# OT tracker for today
resp = requests.post(f"{BUS}/bus/messages", json={
    "from": "kai",
    "to": "cora",
    "type": "tracker_init",
    "priority": "medium",
    "content": {
        "tracker": "daily_ot",
        "date": "2026-03-15",
        "ot_count": 0,
        "target": 3,
        "description": "Outbound touches executed today"
    }
})
print(f"OT tracker initialized: {resp.json().get('id', 'error')[:12]}")

print("\nAll governance rules and trackers written to bus.")

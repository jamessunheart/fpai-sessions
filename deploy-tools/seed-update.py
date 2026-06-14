#!/usr/bin/env python3
"""Update CORA's seed.json with the Full Potential System Handoff framing."""

import json

SEED_FILE = "/opt/fpai/cora-loop/memory/seed.json"

with open(SEED_FILE) as f:
    seed = json.load(f)

seed["context_date"] = "2026-03-15"

seed["system_identity"] = {
    "what_we_are": "A Full Potential ecosystem that diagnoses the real bottleneck, builds custom intelligence around it, connects it to human execution, and circulates value through a larger aligned network.",
    "what_we_are_not": "chatbot setup, coaching, VA agency, BPO, generic automations, software consulting. Each is only a shard.",
    "moat": "The translation layer between deep human truth and living operational infrastructure.",
    "four_moats": [
        "Diagnostic depth — identify the real bottleneck",
        "Tailored AI system — insight becomes custom intelligence layer",
        "Human execution layer — assistants take over where AI can't",
        "Network circulation — client plugs into ecosystem of aligned value"
    ],
    "sequence": "Diagnose → Architect → Operationalize → Circulate"
}

seed["product_ladder"] = [
    "Full Potential Session — diagnostic to identify the true bottleneck",
    "Full Potential System — tailored AI intelligence layer built around the client",
    "Full Potential Assistant — human support attached for execution",
    "Full Potential Network — ecosystem where aligned value circulates"
]

seed["core_pitch"] = {
    "full": "We identify your real bottleneck, build a custom intelligence layer around it, connect that layer to real human support, and plug you into a living network where aligned value can keep moving.",
    "market": "Unlock the real bottleneck keeping you from your Full Potential, then build the support system to move through it."
}

seed["priorities_ranked"] = [
    "1. MARKET CONTACT — Meta Business Manager setup, ad pipeline activation, first real traffic to fullpotential.ai/score",
    "2. Revenue pipeline — lead magnet → assessment → email capture → intake agent → qualification → booking → Sunheart session",
    "3. Fill co-steward role — Cheyenne (deepening), Nicolette Luna (retreat co-creator)",
    "4. Maintain OneBPO operations — Alice managing, monitor cash flow monthly",
    "5. Daily Outbound Touches — minimum 3/day",
    "6. Zen (son in Miami) care coordination — non-negotiable"
]

seed["ecosystem"]["full_potential"] = "Full Potential ecosystem: Session → System → Assistant → Network. One name, one arc, one ecosystem. Assessment page live at fullpotential.ai/score. Intake agent active. Meta ads pipeline built, awaiting ad account ID."

seed["design_principles"] = [
    "The system listens before it speaks",
    "The session is sacred — diagnostic layer is source code",
    "Insight must become structure — conversational truth leaks value",
    "AI-first, human-supported",
    "One ecosystem, not fragmented offers",
    "Reduce cognitive load — client feels held, not flooded",
    "Sunheart Rule: only does what he does superior to AI",
    "Build for proof, not fantasy — reality votes",
    "Governance is part of the product"
]

seed["strategic_warning"] = "The system's own enthusiasm is not signal. Three AIs converging on the same conclusion is not market validation. Demand: actual leads, actual bookings, actual payments, actual completion, actual retention, actual referral behavior. No synthetic traction."

seed["success_30_days"] = [
    "First real inbound lead through fullpotential.ai/score assessment",
    "First Full Potential Session booked with a real human (not seed data)",
    "First session delivered by Sunheart, payment received",
    "Meta ads running with real performance data flowing to CORA",
    "Co-steward role filled or in active negotiation",
    "Sunheart checking Telegram 1-2x/day, system handles the rest"
]

with open(SEED_FILE, "w") as f:
    json.dump(seed, f, indent=2)

print("CORA seed.json updated with Full Potential System Handoff framing")
print("Key changes:")
print("  + system_identity (what we are, four moats, sequence)")
print("  + product_ladder (Session → System → Assistant → Network)")
print("  + core_pitch (full + market versions)")
print("  + design_principles (9 principles)")
print("  + strategic_warning (no synthetic traction)")
print("  + updated priorities (market contact is #1)")
print("  + updated 30-day success metrics (real humans, real payments)")

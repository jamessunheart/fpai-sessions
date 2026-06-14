#!/usr/bin/env python3
"""Patch Adam's USER.md with Full Potential System Handoff framing."""

USER_MD = "/opt/fpai/openclaw/workspace/USER.md"

with open(USER_MD) as f:
    content = f.read()

# 1. Replace P0 Revenue section with updated framing
old_p0 = """### P0 — Revenue Generation

- **Full Potential consulting sessions** are the active product. Three-layer stack:
  - Full Potential Session (one-time deep profile across nine life dimensions)
  - Full Potential Assistant (ongoing retainer)
  - OneBPO as delivery infrastructure behind the assistant

- **Outbound Touches (OT)** is the single most important daily metric. Track it. Measure it. Surface it every morning.

- **Email outreach must be unblocked** (configure Resend in SPARKET immediately)"""

new_p0 = """### P0 — Revenue Generation (MARKET CONTACT)

- **Full Potential is the product.** Not a chatbot. Not coaching. Not a VA agency.
  It is a system that diagnoses the real bottleneck, builds custom intelligence around it,
  connects it to human execution, and circulates value through a larger aligned network.

- **Product ladder (one name, one arc, one ecosystem):**
  - **Full Potential Session** — Diagnostic to identify the true bottleneck
  - **Full Potential System** — Tailored AI intelligence layer built around the client
  - **Full Potential Assistant** — Human support attached for execution
  - **Full Potential Network** — Ecosystem where aligned value circulates

- **Core pitch (market-facing):** Unlock the real bottleneck keeping you from your
  Full Potential, then build the support system to move through it.

- **Sequence:** Diagnose → Architect → Operationalize → Circulate

- **Immediate pipeline:** Meta ads → fullpotential.ai/score assessment → email capture →
  intake agent → qualification → booking → Sunheart delivers session

- **The moat is not the tools.** The moat is the translation layer between deep human truth
  and living operational infrastructure. Very few can do both deep human diagnosis and
  systems translation. That bridge is the rare asset."""

content = content.replace(old_p0, new_p0)

# 2. Update the What You Do NOT Do section with handoff principles
old_donot = """### What You Do NOT Do

- Do NOT reframe directives into strategic frameworks
- Do NOT produce "analysis" when asked for a deliverable
- Do NOT generate meta-commentary about the directive itself
- Do NOT suggest alternative strategies unless explicitly asked
- Do NOT produce theater that looks like work but moves nothing
- Do NOT analyze yourself or the system — validate through real output"""

new_donot = """### What You Do NOT Do

- Do NOT reframe directives into strategic frameworks
- Do NOT produce "analysis" when asked for a deliverable
- Do NOT generate meta-commentary about the directive itself
- Do NOT suggest alternative strategies unless explicitly asked
- Do NOT produce theater that looks like work but moves nothing
- Do NOT analyze yourself or the system — validate through real output
- Do NOT design strategy — you are the executor, not the architect
- Do NOT invent new architecture without a directive
- Do NOT report momentum without evidence — no synthetic traction
- Do NOT confuse internal coherence with external validation

### Permanent Warnings

**The system's own enthusiasm is not signal.** When you report momentum, verify with evidence:
actual leads, actual bookings, actual payments, actual completion, actual retention.

**The Sunheart Rule:** Sunheart does only what he does superior to AI. The system handles
everything else. Every build should reduce drag on Sunheart, not create more of it."""

content = content.replace(old_donot, new_donot)

# 3. Update success metrics
old_success = """## WHAT SUCCESS LOOKS LIKE THIS MONTH (March 2026)

1. ✅ USER.md populated and all cron jobs oriented around it (in progress)
2. Email configured and first autonomous outreach sent
3. At least 5 outbound touches per day tracked and reported
4. Co-steward conversation advanced with either Cheyenne or Nicolette — specific next steps defined
5. Overflow membrane designed and first AI→OneBPO handoff tested
6. Daily briefing running on Telegram with real priorities, not generic status"""

new_success = """## WHAT SUCCESS LOOKS LIKE THIS MONTH (March 2026)

1. First real inbound lead through fullpotential.ai/score assessment
2. First Full Potential Session booked with a real human (not seed data)
3. First session delivered by Sunheart, payment received
4. Meta ads running with real performance data flowing to CORA
5. Co-steward conversation advanced with Cheyenne or Nicolette
6. Sunheart checking Telegram 1-2x/day, system handles the rest"""

content = content.replace(old_success, new_success)

# 4. Update the last-updated timestamp
old_ts = "**Last Updated:** 2026-03-15 05:17 UTC"
new_ts = "**Last Updated:** 2026-03-15 07:20 UTC"
content = content.replace(old_ts, new_ts)

with open(USER_MD, "w") as f:
    f.write(content)

print("Adam USER.md updated with System Handoff framing")
print("Changes:")
print("  + P0 rewritten: Full Potential ecosystem, product ladder, core pitch, moat")
print("  + Added permanent warnings: no synthetic traction, Sunheart Rule")
print("  + Updated success metrics: real leads, real bookings, real payments")

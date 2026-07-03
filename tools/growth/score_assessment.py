#!/usr/bin/env python3
"""Allocation Score engine — the product core behind /assessment.

Turns a lead's 15-minute intake into the promised 48h deliverable: an Allocation
Score (0-100 across capital/time/attention/people/AI/knowledge) + the three
highest-value opportunities + the routed next offer (BBB v1.4). Closes the funnel
loop so the /assessment promise is TRUE, not aspirational.

$0-marginal: runs on the Max subscription via `claude -p`, NOT the metered API.
When a real paying client's confidential data flows, move to a scoped metered key
with a burn-registry row (that's product COGS, ~$0.10-0.50/audit against a $2,500
Blueprint — beautiful CCD). Until then, subscription CLI.

Rubric source: vault 07_COMPOUNDING/Savings Map Kit v1 (§5 Allocation Score).
Routing table: vault 04_DECISION/Offers/BBB v1.4.
Usage:
  score_assessment.py --lead <path>       # score one intake → deliverable md
  score_assessment.py --demo              # score a synthetic lead (proof it works)
"""
import argparse, json, subprocess, sys, os
from pathlib import Path

DIMENSIONS = ["capital", "time", "attention", "people", "ai", "knowledge"]
WEIGHTS = {"capital": 30, "time": 20, "attention": 10, "people": 20, "ai": 10, "knowledge": 10}

# weakest-dimension → offer (BBB v1.4)
ROUTE = {
    "capital":   "Savings Split implementation — 25% of verified savings (floor $5k / cap $50k)",
    "time":      "Intelligence Solutions — automation build by AI Builders",
    "people":    "Builder placement or team training",
    "attention": "Founder-level advisory / consulting (human-led, premium)",
    "ai":        "Intelligence Partnership — $2-5k/mo, quarterly re-audits",
    "knowledge": "Intelligence Partnership — $2-5k/mo, quarterly re-audits",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {"type": "object", "properties": {d: {"type": "integer"} for d in DIMENSIONS},
                   "required": DIMENSIONS, "additionalProperties": False},
        "opportunities": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "dimension": {"type": "string"},
            "why": {"type": "string"}, "est_annual_value": {"type": "string"}},
            "required": ["title", "dimension", "why", "est_annual_value"], "additionalProperties": False}},
    },
    "required": ["scores", "opportunities"], "additionalProperties": False,
}

PROMPT = """You are the Allocation Intelligence engine behind fullpotential.com/assessment.

Given a business's intake, score how well it allocates each scarce resource (0-100,
where 100 = every unit already flows to its highest-value use, 0 = severe misallocation).
Be honest and specific — a real leak scores LOW (that's the value we find). Base scores
on the intake; where the intake is thin, infer conservatively from the business type and
note the assumption in the opportunity's `why`.

Dimensions: capital, time, attention, people, ai, knowledge.

Then give the THREE highest-value opportunities — each tied to a weak dimension, with a
one-line why and an estimated annual $ value (a range is fine; say "needs data" if truly
unknowable from the intake). Prefer concrete finds (SaaS overlap, manual work AI should do,
under-priced capacity, AI spend not earning).

INTAKE:
{intake}

Return ONLY JSON matching this schema (no prose):
{schema}
"""


def run_claude(prompt: str) -> dict:
    """$0 via the Max subscription CLI. Falls back through model flags if needed."""
    r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
    out = r.stdout.strip()
    # lenient JSON extraction (model may fence or add prose despite instructions)
    if "```" in out:
        out = out.split("```", 2)[1]
        if out.startswith("json"):
            out = out[4:]
    start, end = out.find("{"), out.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in model output: {r.stdout[:300]}")
    return json.loads(out[start:end + 1])


def compute(scores: dict) -> tuple[int, str]:
    total = round(sum(scores[d] * WEIGHTS[d] for d in DIMENSIONS) / sum(WEIGHTS.values()))
    weakest = min(DIMENSIONS, key=lambda d: scores[d])
    return total, weakest


def render(name: str, company: str, scores: dict, total: int, weakest: str, opps: list) -> str:
    bars = "\n".join(
        f"| {d.capitalize():10} | {scores[d]:3} | {'█' * (scores[d] // 5)}{'░' * (20 - scores[d] // 5)} |"
        for d in DIMENSIONS)
    opp_md = "\n".join(
        f"{i+1}. **{o['title']}** _(weak: {o['dimension']})_ — {o['why']} · **{o['est_annual_value']}**"
        for i, o in enumerate(opps[:3]))
    return f"""# Your Full Potential Assessment — {company or name}

## Allocation Score: **{total}/100**

| Resource   | Score | |
|------------|-----|--------------------|
{bars}

*The Allocation Score measures how much of each scarce resource already flows to its
highest-value use. Your weakest dimension — **{weakest}** — is where the most capability
is currently trapped.*

## Your 3 highest-value opportunities

{opp_md}

## Recommended next step

Your weakest dimension routes to: **{ROUTE[weakest]}**

_This assessment is yours to keep either way. If you'd like us to implement the top
opportunities, that's the next conversation — you pay out of the value we find._

---
*Powered by FPOS — the Allocation Intelligence Operating System · fullpotential.com*
"""


def parse_intake(text: str) -> tuple[str, str, str]:
    name = company = intake = ""
    for line in text.splitlines():
        low = line.lower()
        if low.startswith("name:"): name = line.split(":", 1)[1].strip()
        elif low.startswith("company") or "company /" in low: company = line.split(":", 1)[1].strip() if ":" in line else ""
        elif low.startswith("bottleneck:") or low.startswith("goal:"): intake += line.split(":", 1)[1].strip() + " "
    return name, company, (intake or text)[:2000]


def score_one(intake_text: str, name: str = "", company: str = "") -> str:
    prompt = PROMPT.format(intake=intake_text, schema=json.dumps(SCHEMA))
    data = run_claude(prompt)
    scores = {d: int(data["scores"].get(d, 50)) for d in DIMENSIONS}
    total, weakest = compute(scores)
    return render(name, company, scores, total, weakest, data.get("opportunities", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.demo:
        intake = ("Wellness studio in Austin — sauna + cold plunge. ~8 staff. Uses Mindbody "
                  "for booking plus a separate email tool and a scheduling spreadsheet the "
                  "front desk fills by hand. Pays for ChatGPT Team but nobody really uses it. "
                  "Wants to grow to a second location this year.")
        print(score_one(intake, "Demo Owner", "Cøntrast ATX (demo)")); return

    if not a.lead:
        print("need --lead <path> or --demo", file=sys.stderr); sys.exit(2)
    text = Path(a.lead).read_text()
    name, company, intake = parse_intake(text)
    result = score_one(intake, name, company)
    if a.out:
        Path(a.out).write_text(result); print(f"→ {a.out}")
    else:
        print(result)


if __name__ == "__main__":
    main()

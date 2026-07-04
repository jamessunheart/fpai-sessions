#!/usr/bin/env python3
"""Full Potential Assessment — Life lens (7 Areas) scoring engine.

The Life-track spine (ACADEMY_PATTERN.md: ONE front door, life lens).
Sibling of tools/growth/score_assessment.py (business lens).

Usage:
  score_life.py --demo                 # scored demo run, prints deliverable
  score_life.py --answers FILE.json    # score real answers
  score_life.py --interactive          # prompt on the terminal (Ember/CLI intake)

Answers file format: {"physical": [7, 5], "mental": [8, 4], ..., "context": {...}}
Output: JSON result + human deliverable to stdout; --out writes the JSON.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
INSTRUMENT = json.loads((HERE / "instrument.json").read_text())


def area_score(vals):
    """Area score = mean of the area's scored answers (0-10)."""
    vals = [max(0, min(10, float(v))) for v in vals]
    return round(sum(vals) / len(vals), 2)


def allocation_score(answers):
    """Allocation Score = mean of 7 area scores × 10 → 0-100."""
    areas = {}
    for area in INSTRUMENT["areas"]:
        key = area["key"]
        if key not in answers or len(answers[key]) != len(area["scored"]):
            raise ValueError(f"missing/short answers for area '{key}'")
        areas[key] = area_score(answers[key])
    score = round(sum(areas.values()) / len(areas) * 10, 1)
    lowest = min(areas, key=areas.get)
    highest = max(areas, key=areas.get)
    return {
        "allocation_score": score,
        "areas": areas,
        "lowest_area": lowest,
        "highest_area": highest,
        "practice_target": lowest,
        "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "instrument_version": INSTRUMENT["version"],
    }


def render(result, context=None):
    label = {a["key"]: a["label"] for a in INSTRUMENT["areas"]}
    lines = [
        "═══ FULL POTENTIAL ASSESSMENT — Life lens ═══",
        f"Allocation Score: {result['allocation_score']} / 100",
        "",
    ]
    for key, val in sorted(result["areas"].items(), key=lambda kv: kv[1]):
        bar = "█" * int(val) + "·" * (10 - int(val))
        marker = "  ← practice target" if key == result["practice_target"] else ""
        lines.append(f"  {label[key]:<14} {bar} {val}{marker}")
    lines += [
        "",
        f"Strongest area: {label[result['highest_area']]}",
        f"This week's focus: {label[result['practice_target']]} — one Golden-Thread practice, "
        "logged 30 sec/day. Re-score Day 14; the delta is the proof.",
    ]
    if context and context.get("spiritual"):
        lines.append(f'Your named AIM: "{context["spiritual"]}"')
    return "\n".join(lines)


def demo():
    answers = {
        "physical": [6, 5], "mental": [7, 4], "spiritual": [8, 7],
        "social": [5, 4], "emotional": [6, 6], "financial": [4, 5],
        "environmental": [8, 8],
    }
    context = {"spiritual": "Build the village that shows paradise is practical."}
    return answers, context


def interactive():
    answers, context = {}, {}
    for area in INSTRUMENT["areas"]:
        vals = []
        print(f"\n— {area['label']} —")
        for q in area["scored"]:
            while True:
                raw = input(f"  {q} [0-10]: ").strip()
                try:
                    vals.append(max(0, min(10, float(raw))))
                    break
                except ValueError:
                    print("    enter a number 0-10")
        answers[area["key"]] = vals
        ctx = input(f"  {area['context']} ").strip()
        if ctx:
            context[area["key"]] = ctx
    return answers, context


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--answers", type=Path)
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--out", type=Path, help="write result JSON here")
    args = p.parse_args()

    if args.demo:
        answers, context = demo()
    elif args.interactive:
        answers, context = interactive()
    elif args.answers:
        data = json.loads(args.answers.read_text())
        context = data.pop("context", {})
        answers = data
    else:
        p.print_help()
        return 1

    result = allocation_score(answers)
    result["context"] = context
    print(render(result, context))
    if args.out:
        args.out.write_text(json.dumps(result, indent=2))
        print(f"\n[written: {args.out}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

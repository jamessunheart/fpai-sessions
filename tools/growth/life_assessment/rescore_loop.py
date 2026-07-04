#!/usr/bin/env python3
"""Life lens Day 1-13 check-in loop and internal cohort export.

Formal scores come only from score_life.py on Day 0 and Day 14. Daily text or
voice-note transcripts provide a bounded conversational nudge: one area, +/-1,
floor 0, ceiling 10, max one nudge per area per participant per day.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.growth.life_assessment import score_life

STATE_DIR = Path(os.environ.get("FPAI_LIFE_ASSESSMENT_DIR", "~/.config/fpai/life_assessment")).expanduser()

AREA_TERMS = {
    "physical": ("body", "sleep", "energy", "movement", "exercise", "nutrition", "tired"),
    "mental": ("mind", "focus", "decision", "fog", "loop", "clarity", "thinking"),
    "spiritual": ("aim", "purpose", "meaning", "alignment", "prayer", "soul", "spirit"),
    "social": ("friend", "people", "support", "conversation", "lonely", "family", "team"),
    "emotional": ("emotion", "feel", "reactive", "overwhelmed", "regulated", "anger", "sad"),
    "financial": ("money", "spend", "budget", "cash", "income", "debt", "financial"),
    "environmental": ("home", "workspace", "room", "nature", "environment", "clutter", "place"),
}
NEGATIVE_TERMS = ("bad", "worse", "low", "stuck", "fog", "tired", "overwhelmed", "lonely", "debt", "clutter", "hard")
POSITIVE_TERMS = ("better", "good", "clear", "steady", "aligned", "supported", "calm", "energized", "improved", "grateful")


def _participant_path(participant_id: str, state_dir: Path = STATE_DIR) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", participant_id).strip("-") or "participant"
    return state_dir / f"{safe}.json"


def load_participant(participant_id: str, state_dir: Path = STATE_DIR) -> dict:
    path = _participant_path(participant_id, state_dir)
    if not path.exists():
        raise FileNotFoundError(f"unknown participant: {participant_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_participant(state: dict, state_dir: Path = STATE_DIR) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = _participant_path(state["participant_id"], state_dir)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def start_participant(participant_id: str, answers: dict, context: dict | None = None,
                      state_dir: Path = STATE_DIR) -> dict:
    result = score_life.allocation_score(answers)
    result["context"] = context or {}
    state = {
        "participant_id": participant_id,
        "instrument_version": result["instrument_version"],
        "day0": result,
        "day14": None,
        "running_areas": dict(result["areas"]),
        "nudges": [],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save_participant(state, state_dir)
    return state


def classify_area(text: str) -> str:
    low = (text or "").lower()
    scores = {
        area: sum(1 for term in terms if term in low)
        for area, terms in AREA_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "mental"


def nudge_direction(text: str) -> int:
    low = (text or "").lower()
    positive = sum(1 for term in POSITIVE_TERMS if term in low)
    negative = sum(1 for term in NEGATIVE_TERMS if term in low)
    return 1 if positive >= negative else -1


def apply_checkin(participant_id: str, text: str, *, when: str | None = None,
                  state_dir: Path = STATE_DIR) -> dict:
    state = load_participant(participant_id, state_dir)
    day = when or date.today().isoformat()
    area = classify_area(text)
    if any(n["date"] == day and n["area"] == area for n in state.get("nudges", [])):
        return {"applied": False, "area": area, "message": f"{area} already heard today. Keep it conversational."}

    delta = nudge_direction(text)
    current = float(state["running_areas"][area])
    updated = round(max(0, min(10, current + delta)), 2)
    state["running_areas"][area] = updated
    state.setdefault("nudges", []).append({
        "date": day,
        "area": area,
        "delta": delta,
        "text": text[:500],
    })
    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_participant(state, state_dir)
    direction = "up" if delta > 0 else "down"
    return {"applied": True, "area": area, "delta": delta, "message": f"I heard {area}. Noted one {direction} nudge for today."}


def record_day14(participant_id: str, answers: dict, context: dict | None = None,
                 state_dir: Path = STATE_DIR) -> dict:
    state = load_participant(participant_id, state_dir)
    result = score_life.allocation_score(answers)
    result["context"] = context or {}
    state["day14"] = result
    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_participant(state, state_dir)
    return state


def cohort_report(state_dir: Path = STATE_DIR) -> dict:
    rows = []
    for path in sorted(state_dir.glob("*.json")):
        state = json.loads(path.read_text(encoding="utf-8"))
        day0 = state.get("day0") or {}
        day14 = state.get("day14") or {}
        if not day14:
            continue
        deltas = {
            area["key"]: round(float(day14["areas"][area["key"]]) - float(day0["areas"][area["key"]]), 2)
            for area in score_life.INSTRUMENT["areas"]
        }
        rows.append({
            "participant_id": state["participant_id"],
            "day0_score": day0.get("allocation_score"),
            "day14_score": day14.get("allocation_score"),
            "score_delta": round(float(day14["allocation_score"]) - float(day0["allocation_score"]), 2),
            "area_deltas": deltas,
            "day0_target": day0.get("practice_target"),
            "day14_target": day14.get("practice_target"),
        })
    return {"count": len(rows), "participants": rows}


def write_csv(report: dict, out: Path) -> None:
    fields = ["participant_id", "day0_score", "day14_score", "score_delta", "day0_target", "day14_target"]
    area_fields = [f"{area['key']}_delta" for area in score_life.INSTRUMENT["areas"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + area_fields)
        writer.writeheader()
        for row in report["participants"]:
            flat = {key: row[key] for key in fields}
            flat.update({f"{key}_delta": value for key, value in row["area_deltas"].items()})
            writer.writerow(flat)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=STATE_DIR)
    sub = parser.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("start")
    start.add_argument("participant_id")
    start.add_argument("--answers", type=Path, required=True)
    checkin = sub.add_parser("checkin")
    checkin.add_argument("participant_id")
    checkin.add_argument("text")
    checkin.add_argument("--date")
    day14 = sub.add_parser("day14")
    day14.add_argument("participant_id")
    day14.add_argument("--answers", type=Path, required=True)
    report = sub.add_parser("report")
    report.add_argument("--csv", type=Path)
    args = parser.parse_args()

    if args.cmd == "start":
        data = json.loads(args.answers.read_text(encoding="utf-8"))
        context = data.pop("context", {})
        print(json.dumps(start_participant(args.participant_id, data, context, args.state_dir), indent=2))
    elif args.cmd == "checkin":
        print(json.dumps(apply_checkin(args.participant_id, args.text, when=args.date, state_dir=args.state_dir), indent=2))
    elif args.cmd == "day14":
        data = json.loads(args.answers.read_text(encoding="utf-8"))
        context = data.pop("context", {})
        print(json.dumps(record_day14(args.participant_id, data, context, args.state_dir), indent=2))
    elif args.cmd == "report":
        data = cohort_report(args.state_dir)
        if args.csv:
            write_csv(data, args.csv)
        print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

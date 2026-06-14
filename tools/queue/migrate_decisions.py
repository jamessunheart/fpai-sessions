#!/usr/bin/env python3
"""Migrate live DECISIONS open items into HUMAN_EDGE_QUEUE."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from tools.queue import build


DEFAULT_VAULT = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~md~obsidian"
    / "Documents"
    / "FPOS"
    / "Full Potential OS"
)
DEFAULT_DECISIONS = DEFAULT_VAULT / "00_MEMORY" / "DECISIONS.md"


def clean_inline(text: str) -> str:
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "decision-" + slug[:64].strip("-")


def stream_for(question: str, body: str) -> str:
    text = f"{question} {body}".lower()
    if any(k in text for k in ("amex", "yield", "capital", "trust wallet", "$")):
        return "Treasury"
    if any(k in text for k in ("butr", "counsel", "legal")):
        return "Legal"
    if any(k in text for k in ("camp zen", "village", "atlas", "jojo")):
        return "Zen"
    if any(k in text for k in ("codex", "build", "self-standing", "system")):
        return "Game"
    return "Ventures"


def verbs_from(answer_line: str) -> list[str]:
    quoted = [clean_inline(v) for v in re.findall(r'"([^"]+)"', answer_line)]
    backticked = [clean_inline(v) for v in re.findall(r"`([^`]+)`", answer_line)]
    if quoted:
        verbs = quoted
    elif backticked:
        verbs = backticked
    else:
        before_arrow = answer_line.split("→", 1)[0]
        before_or = before_arrow.split(" or ", 1)[0]
        before_dot = before_or.split(".", 1)[0]
        verbs = [clean_inline(re.sub(r"^(?:say|answer):?\s+", "", before_dot, flags=re.I))]
    if "checkpoint" not in {v.lower() for v in verbs}:
        verbs.append("checkpoint")
    return [v for v in verbs if v]


def parse_open_decisions(text: str) -> list[dict[str, object]]:
    if "## 🟡 Open" not in text:
        return []
    seg = text.split("## 🟡 Open", 1)[1].split("\n## ", 1)[0]
    pattern = re.compile(
        r"^- (?P<marker>[🔴🟡🎁]) \*\*(?P<question>.+?)\*\* (?P<body>.*?)\n\s*↳\s*answer:\s*(?P<answer>.+?)(?=\n- [🔴🟡🎁] |\n\n- [🔴🟡🎁] |\n\n---|\Z)",
        re.S | re.M,
    )
    gates = []
    for match in pattern.finditer(seg):
        marker = match.group("marker")
        question = clean_inline(match.group("question"))
        body = clean_inline(match.group("body").lstrip("— "))
        answer = match.group("answer")
        gates.append(
            {
                "gate_id": slugify(question),
                "stream": stream_for(question, body),
                "question": question,
                "verbs": verbs_from(answer),
                "blocking": True,
                "urgent": marker == "🔴",
            }
        )
    return gates


def migrate(decisions_path: Path, queue_path: Path, render_decisions: bool) -> list[dict[str, object]]:
    text = decisions_path.read_text(encoding="utf-8", errors="ignore")
    gates = parse_open_decisions(text)
    added = []
    for gate in gates:
        added.append(build.add_gate(path=queue_path, **gate))
    if render_decisions:
        build.write_decisions_surface(decisions_path, build.load_queue(queue_path))
    return added


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate DECISIONS open items into HUMAN_EDGE_QUEUE.")
    ap.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    ap.add_argument("--queue", type=Path, default=build.DEFAULT_JSON)
    ap.add_argument("--render-decisions", action="store_true")
    args = ap.parse_args()

    added = migrate(args.decisions, args.queue, args.render_decisions)
    print(f"migrated {len(added)} gates into {args.queue}")
    for gate in added:
        print(f"- {gate['id']} · {gate['stream']} · {gate['question']}")


if __name__ == "__main__":
    main()

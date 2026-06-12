#!/usr/bin/env python3
"""Canonical human-edge queue.

The queue is data, not action. It records questions that need James's verb and
renders the human-facing surfaces that previously parsed hand-maintained notes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
DEFAULT_MD = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.md"

STREAMS = {"Play", "Game", "Zen", "Ventures", "Treasury", "Legal", "Cheyenne"}
STATES = {"open", "answered", "expired"}


def _json_path(path: Path | str | None = None) -> Path:
    if path:
        return Path(path)
    return Path(os.environ.get("FPAI_HUMAN_EDGE_QUEUE_JSON", DEFAULT_JSON))


def _md_path(json_path: Path, path: Path | str | None = None) -> Path:
    if path:
        return Path(path)
    return Path(os.environ.get("FPAI_HUMAN_EDGE_QUEUE_MD", json_path.with_suffix(".md")))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_queue(path: Path | str | None = None) -> dict[str, Any]:
    qpath = _json_path(path)
    if not qpath.exists():
        return {"version": 1, "gates": []}
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid human-edge queue JSON: {qpath}") from exc
    gates = data.get("gates", [])
    if not isinstance(gates, list):
        raise ValueError("human-edge queue must contain a gates list")
    return {"version": int(data.get("version", 1)), "gates": [_normalize_gate(g) for g in gates]}


def save_queue(
    data: dict[str, Any],
    path: Path | str | None = None,
    md_path: Path | str | None = None,
) -> None:
    qpath = _json_path(path)
    mpath = _md_path(qpath, md_path)
    normalized = {"version": int(data.get("version", 1)), "gates": [_normalize_gate(g) for g in data.get("gates", [])]}
    qpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    qpath.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mpath.write_text(render_queue_markdown(normalized), encoding="utf-8")


def _normalize_gate(raw: dict[str, Any]) -> dict[str, Any]:
    gate = {
        "id": str(raw.get("id", "")).strip(),
        "surfaced": str(raw.get("surfaced") or raw.get("surfaced_ts") or "").strip(),
        "stream": str(raw.get("stream", "")).strip(),
        "question": str(raw.get("question", "")).strip(),
        "verbs": [str(v).strip() for v in raw.get("verbs", []) if str(v).strip()],
        "blocking": bool(raw.get("blocking", False)),
        "urgent": bool(raw.get("urgent", False)),
        "state": str(raw.get("state", "open")).strip() or "open",
        "answer": raw.get("answer", ""),
    }
    if not gate["id"]:
        raise ValueError("human-edge gate requires id")
    if not gate["surfaced"]:
        gate["surfaced"] = utc_now()
    if gate["stream"] not in STREAMS:
        raise ValueError(f"invalid human-edge stream for {gate['id']}: {gate['stream']}")
    if not gate["question"]:
        raise ValueError(f"human-edge gate {gate['id']} requires question")
    if not gate["verbs"]:
        raise ValueError(f"human-edge gate {gate['id']} requires at least one verb")
    if gate["state"] not in STATES:
        raise ValueError(f"invalid human-edge state for {gate['id']}: {gate['state']}")
    if gate["answer"] is None:
        gate["answer"] = ""
    gate["answer"] = str(gate["answer"]).strip()
    return gate


def add_gate(
    *,
    gate_id: str,
    stream: str,
    question: str,
    verbs: list[str],
    blocking: bool = True,
    urgent: bool = False,
    surfaced: str | None = None,
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Add an open gate if its id is new; duplicate ids are deduped."""
    data = load_queue(path)
    for gate in data["gates"]:
        if gate["id"] == gate_id:
            save_queue(data, path)
            return gate
    gate = _normalize_gate(
        {
            "id": gate_id,
            "surfaced": surfaced or utc_now(),
            "stream": stream,
            "question": question,
            "verbs": verbs,
            "blocking": blocking,
            "urgent": urgent,
            "state": "open",
            "answer": "",
        }
    )
    data["gates"].append(gate)
    save_queue(data, path)
    return gate


def answer_gate(gate_id: str, answer: str, path: Path | str | None = None) -> dict[str, Any]:
    """Record James's verb. This is the only helper that closes a gate."""
    data = load_queue(path)
    for gate in data["gates"]:
        if gate["id"] != gate_id:
            continue
        if answer not in gate["verbs"]:
            raise ValueError(f"answer for {gate_id} must be one of: {', '.join(gate['verbs'])}")
        gate["state"] = "answered"
        gate["answer"] = answer
        save_queue(data, path)
        return gate
    raise KeyError(f"human-edge gate not found: {gate_id}")


def open_gates(path: Path | str | None = None) -> list[dict[str, Any]]:
    gates = [g for g in load_queue(path)["gates"] if g["state"] == "open"]
    return sorted(gates, key=lambda g: (not g["urgent"], not g["blocking"]))


def gate_affordance(gate: dict[str, Any]) -> str:
    return "reply " + " / ".join(f'"{verb}"' for verb in gate["verbs"])


def gate_unblock(gate: dict[str, Any]) -> str:
    bits = [gate["stream"]]
    if gate["blocking"]:
        bits.append("blocking")
    if gate["urgent"]:
        bits.append("urgent: 🔴")
    return " · ".join(bits)


def decision_tuples(path: Path | str | None = None) -> list[tuple[str, str, str]]:
    return [(g["question"], gate_unblock(g), gate_affordance(g)) for g in open_gates(path)]


HOME_DECIDE_TOP_N = 3


def render_home_decide(data: dict[str, Any] | None = None, top_n: int = HOME_DECIDE_TOP_N) -> str:
    """Top N gates rendered in full; the rest fold into a collapsed Obsidian
    callout so HOME stays a top-3 surface. As top gates are answered, the
    next ones rise out of the fold on the following render."""
    gates = open_gates_from_data(data or load_queue())
    if not gates:
        return "_No open human-edge gates._"
    blocks = [
        f"**{gate['question']}**\n"
        f"Stream: `{gate['stream']}` · id: `{gate['id']}`\n"
        "Options: " + " / ".join(f"`{verb}`" for verb in gate["verbs"]) + "\n"
        "Your answer: `...`"
        for gate in gates[:top_n]
    ]
    rest = gates[top_n:]
    if rest:
        fold = [f"> [!todo]- {len(rest)} more queued — open when the top {len(blocks)} are clear"]
        for gate in rest:
            marker = "🔴" if gate["urgent"] else "🟡"
            fold.append(">")
            fold.append(f"> {marker} **{gate['question']}** · `{gate['stream']}` · id: `{gate['id']}`")
            fold.append("> ↳ answer: " + " / ".join(f"`{verb}`" for verb in gate["verbs"]))
        blocks.append("\n".join(fold))
    return "\n\n".join(blocks)


def open_gates_from_data(data: dict[str, Any]) -> list[dict[str, Any]]:
    gates = [g for g in data["gates"] if g["state"] == "open"]
    return sorted(gates, key=lambda g: (not g["urgent"], not g["blocking"]))


def render_decisions(data: dict[str, Any] | None = None) -> str:
    q = data or load_queue()
    lines = ["# DECISIONS", "", "*Rendered from `core/STATE/HUMAN_EDGE_QUEUE.json`.*", "", "## 🟡 Open", ""]
    lines.extend(render_decisions_open_lines(q))
    lines.extend(["", "## ✅ Answered", ""])
    answered = [g for g in q["gates"] if g["state"] == "answered"]
    if answered:
        for gate in answered:
            lines.append(f"- ✅ **{gate['question']}** ({gate['stream']} · `{gate['id']}`) — `{gate['answer']}`")
    else:
        lines.append("_No answered human-edge gates._")
    return "\n".join(lines).rstrip() + "\n"


def render_decisions_open_lines(data: dict[str, Any] | None = None) -> list[str]:
    q = data or load_queue()
    lines = ["*Rendered from `core/STATE/HUMAN_EDGE_QUEUE.json`.*", ""]
    open_items = open_gates_from_data(q)
    if open_items:
        for gate in open_items:
            marker = "🔴" if gate["urgent"] else "🟡"
            lines.append(f"- {marker} **{gate['question']}** ({gate['stream']} · `{gate['id']}`) — {gate_unblock(gate)}")
            lines.append(f"  ↳ answer: {' / '.join(f'`{verb}`' for verb in gate['verbs'])}")
    else:
        lines.append("_No open human-edge gates._")
    return lines


def render_decisions_open_block(data: dict[str, Any] | None = None) -> str:
    return "\n".join(render_decisions_open_lines(data)).rstrip() + "\n"


def write_decisions_surface(decisions_path: Path | str, data: dict[str, Any] | None = None) -> bool:
    """Replace the DECISIONS Open section with the queue render, preserving other lanes."""
    path = Path(decisions_path)
    doc = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else "# DECISIONS\n\n## 🟡 Open\n\n"
    heading = "## 🟡 Open — your call  (ranked · top 3 surface in today's note)"
    block = f"{heading}\n\n{render_decisions_open_block(data)}"
    if "## 🟡 Open" in doc:
        new = re.sub(r"## 🟡 Open.*?(?=\n## |\Z)", block + "\n", doc, count=1, flags=re.S)
    else:
        new = doc.rstrip() + "\n\n" + block + "\n"
    if new != doc:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def render_queue_markdown(data: dict[str, Any] | None = None) -> str:
    q = data or load_queue()
    lines = [
        "# HUMAN EDGE QUEUE",
        "",
        "*Canonical human-edge gate queue. Generated by `tools/queue/build.py`.*",
        "",
    ]
    for state, heading in (("open", "Open"), ("answered", "Answered"), ("expired", "Expired")):
        lines.extend([f"## {heading}", ""])
        gates = [g for g in q["gates"] if g["state"] == state]
        if not gates:
            lines.extend([f"_No {state} human-edge gates._", ""])
            continue
        for gate in sorted(gates, key=lambda g: (not g["urgent"], not g["blocking"])):
            flags = []
            if gate["blocking"]:
                flags.append("blocking")
            if gate["urgent"]:
                flags.append("urgent: 🔴")
            lines.append(f"### {gate['id']}")
            lines.append(f"- surfaced: `{gate['surfaced']}`")
            lines.append(f"- stream: `{gate['stream']}`")
            lines.append(f"- question: {gate['question']}")
            lines.append("- verbs: " + " / ".join(f"`{verb}`" for verb in gate["verbs"]))
            lines.append(f"- blocking: `{str(gate['blocking']).lower()}`")
            lines.append(f"- urgent: `{str(gate['urgent']).lower()}`")
            lines.append(f"- state: `{gate['state']}`")
            lines.append(f"- answer: `{gate['answer']}`" if gate["answer"] else "- answer:")
            if flags:
                lines.append("- flags: " + " · ".join(flags))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build and maintain the human-edge queue.")
    sub = ap.add_subparsers(dest="cmd")
    add = sub.add_parser("add")
    add.add_argument("--id", required=True)
    add.add_argument("--stream", required=True, choices=sorted(STREAMS))
    add.add_argument("--question", required=True)
    add.add_argument("--verbs", required=True, help="Comma-separated one-tap replies")
    add.add_argument("--blocking", action=argparse.BooleanOptionalAction, default=True)
    add.add_argument("--urgent", action="store_true")
    ans = sub.add_parser("answer")
    ans.add_argument("--id", required=True)
    ans.add_argument("--answer", required=True)
    sub.add_parser("render")
    args = ap.parse_args()

    if args.cmd == "add":
        gate = add_gate(
            gate_id=args.id,
            stream=args.stream,
            question=args.question,
            verbs=[v.strip() for v in args.verbs.split(",") if v.strip()],
            blocking=args.blocking,
            urgent=args.urgent,
        )
        print(f"gate {gate['id']} open")
    elif args.cmd == "answer":
        gate = answer_gate(args.id, args.answer)
        print(f"gate {gate['id']} answered: {gate['answer']}")
    else:
        data = load_queue()
        save_queue(data)
        print(f"rendered {len(data['gates'])} gates")


if __name__ == "__main__":
    main()

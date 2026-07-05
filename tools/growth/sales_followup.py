#!/usr/bin/env python3
"""Guarded per-lead sales follow-up agent for assessment leads.

Default posture: draft, track, and gate. It never sends to a real prospect unless
James approves a gate externally or sets SALES_AUTOSEND=1 for standing approval.
It never charges or marks a close as won automatically.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from tools.queue.build import add_gate
from tools.reserved.classify import is_reserved

SIGNATURE = "James Sunheart + AI · Full Potential · fullpotential.com  ·  Allocation Intelligence · fullpotential.ai"
COMPLIANCE_COPY = "You are receiving this because you requested a Full Potential Assessment. Reply unsubscribe to stop."
RESERVED_WALLS = (
    "Reserved wall: every public send needs James approval unless SALES_AUTOSEND=1 is set.",
    "Reserved wall: payment, charging, and final close remain James-only money decisions.",
)
DEFAULT_STATE = Path(os.environ.get("SALES_FOLLOWUP_STATE", "~/.config/fpai/sales_followup/state.json")).expanduser()
DEFAULT_LEDGER = Path(os.environ.get("SALES_FOLLOWUP_LEDGER", "~/.config/fpai/sales_followup/touches.jsonl")).expanduser()
DEFAULT_LANE = Path(os.environ.get("SALES_FOLLOWUP_LANE", "docs/codex/SALES_FOLLOWUP_LANE.md"))
DEFAULT_QUEUE = Path(os.environ.get("FPAI_HUMAN_EDGE_QUEUE_JSON", "core/STATE/HUMAN_EDGE_QUEUE.json"))
DEFAULT_BRAIN_INDEX_DSN = os.environ.get("BRAIN_INDEX_DSN") or os.environ.get("DATABASE_URL") or ""
KILL = Path(os.environ.get("SALES_FOLLOWUP_KILL", "/opt/fpai-build/.sales_followup_disabled"))
MIN_SECONDS_BETWEEN_SENDS = int(os.environ.get("SALES_FOLLOWUP_MIN_SECONDS", "3600"))

STAGES = ("delivered", "engaged", "booked", "proposed", "won", "lost")
TOUCH_KINDS = ("value_followup", "soft_booking_cta", "blueprint_offer", "objection_handling")


@dataclasses.dataclass(frozen=True)
class LeadContext:
    lead_id: str
    name: str
    email: str
    company: str
    bottleneck: str
    allocation_score: int | None
    weakest_dimension: str
    opportunities: list[str]
    source_path: str = ""


@dataclasses.dataclass(frozen=True)
class TouchDraft:
    touch_id: str
    kind: str
    subject: str
    body: str
    send_after_days: int
    stage_after_send: str
    reserved_wall: str = "public_send"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ReplyDraft:
    reply_id: str
    subject: str
    body: str
    inferred_stage: str
    gate_id: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1(":".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def parse_frontmatter(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    source = match.group(1).splitlines() if match else text.splitlines()
    for line in source:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower().replace(" ", "_")] = value.strip().strip('"')
    return data


def load_lead_context(lead_path: Path, deliverable_path: Path | None = None) -> LeadContext:
    lead_text = lead_path.read_text(encoding="utf-8")
    fields = parse_frontmatter(lead_text)
    body_text = re.sub(r"^---\n.*?\n---", "", lead_text, flags=re.S)
    deliverable = deliverable_path.read_text(encoding="utf-8") if deliverable_path and deliverable_path.exists() else ""
    lead_id = lead_path.stem
    return LeadContext(
        lead_id=lead_id,
        name=fields.get("name", ""),
        email=fields.get("email", "").lower(),
        company=fields.get("company") or fields.get("company_name", ""),
        bottleneck=fields.get("bottleneck") or fields.get("goal") or _extract_bottleneck(body_text),
        allocation_score=_extract_allocation_score(deliverable),
        weakest_dimension=_extract_weakest_dimension(deliverable) or _infer_weakest_dimension(lead_text + "\n" + deliverable),
        opportunities=_extract_opportunities(deliverable),
        source_path=str(lead_path),
    )


def draft_sequence(
    context: LeadContext,
    deliverable_text: str = "",
    *,
    model_runner: Callable[[str], dict[str, Any]] | None = None,
) -> list[TouchDraft]:
    if model_runner is None:
        model_runner = _run_sales_model
    prompt = _sequence_prompt(context, deliverable_text)
    try:
        raw = model_runner(prompt)
        touches = _touches_from_model(context, raw)
    except Exception:
        touches = _fallback_sequence(context)
    return touches


def draft_reply(
    context: LeadContext,
    reply: dict[str, Any],
    *,
    model_runner: Callable[[str], dict[str, Any]] | None = None,
) -> ReplyDraft:
    inferred_stage = infer_stage_from_reply(str(reply.get("body") or reply.get("text") or ""))
    subject = _reply_subject(str(reply.get("subject") or "your assessment"))
    if model_runner is None:
        model_runner = _run_sales_model
    try:
        raw = model_runner(_reply_prompt(context, reply, inferred_stage))
        body = str(raw.get("body") or "").strip()
        if not body:
            raise ValueError("empty reply body")
    except Exception:
        body = _fallback_reply_body(context, reply, inferred_stage)
    body = with_signature_and_compliance(body)
    gate_id = f"sales-reply-send-{stable_id('gate', context.lead_id, subject, body)}"
    return ReplyDraft(
        reply_id=stable_id("reply", context.lead_id, str(reply.get("id") or ""), body),
        subject=subject,
        body=body,
        inferred_stage=inferred_stage,
        gate_id=gate_id,
    )


def plan_for_lead(
    lead_path: Path,
    deliverable_path: Path | None = None,
    *,
    replies: list[dict[str, Any]] | None = None,
    model_runner: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    context = load_lead_context(lead_path, deliverable_path)
    deliverable_text = deliverable_path.read_text(encoding="utf-8") if deliverable_path and deliverable_path.exists() else ""
    sequence = draft_sequence(context, deliverable_text, model_runner=model_runner)
    reply_drafts = [draft_reply(context, item, model_runner=model_runner) for item in replies or []]
    return {
        "schema": "fpai.sales.followup.v1",
        "generated_at": now_utc(),
        "reserved_walls": list(RESERVED_WALLS),
        "lead": dataclasses.asdict(context),
        "stage": infer_stage_from_replies(replies or []) or "delivered",
        "sequence": [touch.to_dict() for touch in sequence],
        "reply_drafts": [item.to_dict() for item in reply_drafts],
    }


def stage_plan(
    plan: dict[str, Any],
    *,
    lane_path: Path | str = DEFAULT_LANE,
    queue_path: Path | str = DEFAULT_QUEUE,
    state_path: Path | str = DEFAULT_STATE,
    ledger_path: Path | str = DEFAULT_LEDGER,
    brain_index_dsn: str = DEFAULT_BRAIN_INDEX_DSN,
    sender: Callable[[dict[str, Any], dict[str, Any]], tuple[bool, str]] | None = None,
    live: bool = False,
) -> dict[str, Any]:
    if KILL.exists():
        return {"status": "killed", "sent": [], "gates": [], "lane": None}
    lead = plan["lead"]
    state = load_state(state_path)
    lead_state = state.setdefault(lead["lead_id"], {"stage": "delivered", "engagement": {}, "touches": []})
    lead_state["stage"] = max_stage(str(plan.get("stage") or "delivered"), str(lead_state.get("stage") or "delivered"))
    gates: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []
    standing_approval = os.environ.get("SALES_AUTOSEND") == "1"

    Path(lane_path).parent.mkdir(parents=True, exist_ok=True)
    Path(lane_path).write_text(render_lane(plan, standing_approval=standing_approval), encoding="utf-8")

    for touch in plan.get("sequence", []):
        gate_id = f"sales-send-{touch['touch_id']}"
        if standing_approval and live:
            ok, detail = maybe_send_touch(lead, touch, state=state, sender=sender)
            row = touch_log_row(lead, touch, action="sent" if ok else "held", detail=detail)
            append_jsonl(Path(ledger_path), row)
            if ok:
                sent.append(row)
                lead_state["stage"] = max_stage(lead_state["stage"], touch.get("stage_after_send", "engaged"))
            continue
        gate = add_gate(
            gate_id=gate_id,
            stream="Ventures",
            question=f"Approve sales follow-up to {lead.get('email')}: {touch.get('subject')}",
            verbs=["approve", "edit", "skip"],
            blocking=True,
            urgent=False,
            path=queue_path,
        )
        gates.append(gate)
        append_jsonl(Path(ledger_path), touch_log_row(lead, touch, action="drafted", detail=f"gate:{gate_id}"))

    for reply in plan.get("reply_drafts", []):
        gate = add_gate(
            gate_id=reply["gate_id"],
            stream="Ventures",
            question=f"Approve reply to {lead.get('email')}: {reply.get('subject')}",
            verbs=["approve", "edit", "skip"],
            blocking=True,
            urgent=True,
            path=queue_path,
        )
        gates.append(gate)
        lead_state["stage"] = max_stage(lead_state["stage"], reply.get("inferred_stage", "engaged"))
        append_jsonl(Path(ledger_path), reply_log_row(lead, reply, action="reply_drafted", detail=f"gate:{reply['gate_id']}"))
        if reply.get("inferred_stage") == "proposed":
            close_gate = add_gate(
                gate_id=f"sales-close-{lead['lead_id']}",
                stream="Ventures",
                question=f"Close/payment wall for {lead.get('email')}: James must decide the Blueprint close.",
                verbs=["take-over", "skip"],
                blocking=True,
                urgent=True,
                path=queue_path,
            )
            gates.append(close_gate)
            append_jsonl(
                Path(ledger_path),
                {
                    "ts": now_utc(),
                    "lead_id": lead.get("lead_id", ""),
                    "action": "close_escalated",
                    "detail": f"gate:{close_gate['id']}",
                    "reserved_wall": "payment_close",
                },
            )

    save_state(state, state_path)
    track_brain_index(lead, lead_state, dsn=brain_index_dsn)
    return {"status": "ok", "sent": sent, "gates": gates, "lane": str(lane_path)}


def maybe_send_touch(
    lead: dict[str, Any],
    touch: dict[str, Any],
    *,
    state: dict[str, Any],
    sender: Callable[[dict[str, Any], dict[str, Any]], tuple[bool, str]] | None = None,
) -> tuple[bool, str]:
    if not os.environ.get("SALES_AUTOSEND") == "1":
        return False, "standing approval missing"
    if touch.get("kind") == "close":
        return False, "close/payment reserved for James"
    if not lead.get("email"):
        return False, "missing lead email"
    lead_state = state.setdefault(lead["lead_id"], {"touches": []})
    last_sent = max((float(item.get("sent_at_epoch", 0)) for item in lead_state.get("touches", []) if item.get("action") == "sent"), default=0)
    now_epoch = dt.datetime.now(dt.timezone.utc).timestamp()
    if last_sent and now_epoch - last_sent < MIN_SECONDS_BETWEEN_SENDS:
        return False, "rate-limited"
    if sender is None:
        return False, "no sender configured"
    verdict = is_reserved(f"Send sales follow-up to {lead.get('email')}", {"surface": "email", "stream": "Ventures"})
    if not verdict.get("reserved"):
        return False, "send did not classify as reserved"
    ok, detail = sender(lead, touch)
    if ok:
        lead_state.setdefault("touches", []).append(
            {"touch_id": touch["touch_id"], "action": "sent", "sent_at": now_utc(), "sent_at_epoch": now_epoch}
        )
    return ok, detail


def update_engagement(
    lead_id: str,
    event: str,
    *,
    state_path: Path | str = DEFAULT_STATE,
    ledger_path: Path | str = DEFAULT_LEDGER,
    brain_index_dsn: str = DEFAULT_BRAIN_INDEX_DSN,
) -> dict[str, Any]:
    if event not in {"open", "click", "reply", "booked", "proposed", "won", "lost"}:
        raise ValueError(f"unknown engagement event: {event}")
    state = load_state(state_path)
    lead_state = state.setdefault(lead_id, {"stage": "delivered", "engagement": {}, "touches": []})
    engagement = lead_state.setdefault("engagement", {})
    engagement[event] = int(engagement.get(event, 0)) + 1
    stage_map = {"open": "engaged", "click": "engaged", "reply": "engaged", "booked": "booked", "proposed": "proposed", "won": "won", "lost": "lost"}
    lead_state["stage"] = max_stage(str(lead_state.get("stage") or "delivered"), stage_map[event])
    row = {"ts": now_utc(), "lead_id": lead_id, "action": "engagement", "event": event, "stage": lead_state["stage"]}
    append_jsonl(Path(ledger_path), row)
    save_state(state, state_path)
    track_brain_index({"lead_id": lead_id}, lead_state, dsn=brain_index_dsn)
    return lead_state


def track_brain_index(lead: dict[str, Any], lead_state: dict[str, Any], *, dsn: str = DEFAULT_BRAIN_INDEX_DSN) -> bool:
    if not dsn:
        return False
    try:
        import psycopg2  # type: ignore
    except Exception:
        return False
    payload = json.dumps({"lead": lead, "state": lead_state}, sort_keys=True)
    sql = """
    CREATE TABLE IF NOT EXISTS brain_index.sales_followups (
      lead_id text PRIMARY KEY,
      stage text NOT NULL,
      engagement jsonb NOT NULL,
      payload jsonb NOT NULL,
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    INSERT INTO brain_index.sales_followups (lead_id, stage, engagement, payload, updated_at)
    VALUES (%s, %s, %s::jsonb, %s::jsonb, now())
    ON CONFLICT (lead_id) DO UPDATE SET
      stage = EXCLUDED.stage,
      engagement = EXCLUDED.engagement,
      payload = EXCLUDED.payload,
      updated_at = now();
    """
    try:
        conn = psycopg2.connect(dsn)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        lead.get("lead_id", ""),
                        lead_state.get("stage", "delivered"),
                        json.dumps(lead_state.get("engagement", {}), sort_keys=True),
                        payload,
                    ),
                )
        conn.close()
        return True
    except Exception:
        return False


def render_lane(plan: dict[str, Any], *, standing_approval: bool = False) -> str:
    lead = plan["lead"]
    lines = [
        "# Sales Follow-Up Lane",
        "",
        "*Generated by `tools/growth/sales_followup.py`.*",
        "",
        f"- generated: `{plan.get('generated_at', now_utc())}`",
        f"- lead: `{lead.get('lead_id')}` · {lead.get('name') or '(no name)'} <{lead.get('email') or 'no email'}>",
        f"- company: {lead.get('company') or 'unknown'}",
        f"- stage: `{plan.get('stage', 'delivered')}`",
        f"- standing approval: `{str(standing_approval).lower()}`",
        f"- allocation score: `{lead.get('allocation_score')}`",
        f"- weakest dimension: `{lead.get('weakest_dimension')}`",
        "",
        "## Reserved Walls",
        "",
    ]
    lines.extend(f"- {wall}" for wall in plan.get("reserved_walls", RESERVED_WALLS))
    lines.extend(["", "## Draft Sequence", ""])
    for touch in plan.get("sequence", []):
        lines.extend(
            [
                f"### {touch['touch_id']} · {touch['kind']}",
                f"- subject: {touch['subject']}",
                f"- send after days: `{touch['send_after_days']}`",
                f"- stage after send: `{touch['stage_after_send']}`",
                "",
                "```text",
                touch["body"],
                "```",
                "",
            ]
        )
    lines.extend(["## Reply Drafts", ""])
    if not plan.get("reply_drafts"):
        lines.extend(["_No replies requiring a response staged._", ""])
    for reply in plan.get("reply_drafts", []):
        lines.extend(
            [
                f"### {reply['reply_id']}",
                f"- subject: {reply['subject']}",
                f"- inferred stage: `{reply['inferred_stage']}`",
                f"- gate id: `{reply['gate_id']}`",
                "",
                "```text",
                reply["body"],
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def load_replies(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("reply fixture must be a JSON list")
    return [item for item in data if isinstance(item, dict)]


def load_state(path: Path | str = DEFAULT_STATE) -> dict[str, Any]:
    state_path = Path(path)
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict[str, Any], path: Path | str = DEFAULT_STATE) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def touch_log_row(lead: dict[str, Any], touch: dict[str, Any], *, action: str, detail: str) -> dict[str, Any]:
    return {
        "ts": now_utc(),
        "lead_id": lead.get("lead_id", ""),
        "email_hash": hashlib.sha256(str(lead.get("email", "")).lower().encode("utf-8")).hexdigest() if lead.get("email") else "",
        "touch_id": touch.get("touch_id", ""),
        "kind": touch.get("kind", ""),
        "action": action,
        "detail": detail,
        "reserved_wall": touch.get("reserved_wall", "public_send"),
    }


def reply_log_row(lead: dict[str, Any], reply: dict[str, Any], *, action: str, detail: str) -> dict[str, Any]:
    return {
        "ts": now_utc(),
        "lead_id": lead.get("lead_id", ""),
        "reply_id": reply.get("reply_id", ""),
        "action": action,
        "detail": detail,
        "stage": reply.get("inferred_stage", "engaged"),
    }


def infer_stage_from_reply(text: str) -> str:
    low = text.lower()
    if any(term in low for term in ("booked", "calendar invite", "see you", "scheduled")):
        return "booked"
    if any(term in low for term in ("price", "proposal", "blueprint", "cost", "package")):
        return "proposed"
    if any(term in low for term in ("not interested", "unsubscribe", "stop", "no thanks")):
        return "lost"
    if any(term in low for term in ("yes", "interested", "tell me more", "question", "?")):
        return "engaged"
    return "engaged"


def infer_stage_from_replies(replies: list[dict[str, Any]]) -> str:
    stage = "delivered"
    for reply in replies:
        stage = max_stage(stage, infer_stage_from_reply(str(reply.get("body") or reply.get("text") or "")))
    return stage


def max_stage(a: str, b: str) -> str:
    order = {stage: index for index, stage in enumerate(STAGES)}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def with_signature_and_compliance(body: str) -> str:
    clean = body.strip()
    if SIGNATURE not in clean:
        clean = f"{clean}\n\n--\n{SIGNATURE}"
    if COMPLIANCE_COPY not in clean:
        clean = f"{clean}\n\n{COMPLIANCE_COPY}"
    return clean


def _extract_bottleneck(text: str) -> str:
    for line in text.splitlines():
        low = line.lower()
        if low.startswith("bottleneck:") or low.startswith("goal:"):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_allocation_score(text: str) -> int | None:
    match = re.search(r"Allocation Score:\s*\*\*(\d{1,3})/100\*\*", text)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def _extract_weakest_dimension(text: str) -> str:
    match = re.search(r"weakest dimension\s*[—-]\s*\*\*([a-z]+)\*\*", text, re.I)
    return match.group(1).lower() if match else ""


def _extract_opportunities(text: str) -> list[str]:
    lines = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## Your 3 highest-value opportunities"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and re.match(r"\d+\.\s+\*\*", line.strip()):
            lines.append(re.sub(r"\s+", " ", line.strip()))
    return lines[:3]


def _infer_weakest_dimension(text: str) -> str:
    low = text.lower()
    hints = {
        "time": ("manual", "hours", "spreadsheet", "handoff", "slow"),
        "capital": ("cash", "spend", "waste", "saas", "budget"),
        "attention": ("focus", "overwhelmed", "priority", "decision"),
        "people": ("hire", "team", "capacity", "delegation", "training"),
        "ai": ("ai", "automation", "chatgpt", "zapier"),
        "knowledge": ("knowledge", "documentation", "reporting", "silo"),
    }
    scored = [(sum(1 for term in terms if term in low), dimension) for dimension, terms in hints.items()]
    scored.sort(reverse=True)
    return scored[0][1] if scored and scored[0][0] else "time"


def _sequence_prompt(context: LeadContext, deliverable_text: str) -> str:
    return f"""You are James Sunheart + AI drafting sales follow-up after a Full Potential Assessment.
Draft a four-touch sequence only. Do not claim James has sent it. Do not invent pricing, scarcity,
guarantees, payment links, or a close. Every touch must be honest that James + AI are writing.

Lead:
{json.dumps(dataclasses.asdict(context), indent=2)}

Assessment deliverable:
{deliverable_text[:6000]}

Return JSON:
{{"touches":[{{"kind":"value_followup|soft_booking_cta|blueprint_offer|objection_handling","subject":"...","body":"...","send_after_days":0,"stage_after_send":"engaged|booked|proposed"}}]}}
"""


def _reply_prompt(context: LeadContext, reply: dict[str, Any], inferred_stage: str) -> str:
    return f"""Draft a context-aware reply for James review. No public send is approved yet.
Do not ask for payment or mark the close won. If the person asks to buy or pay, escalate to James.

Lead:
{json.dumps(dataclasses.asdict(context), indent=2)}

Inferred stage: {inferred_stage}
Reply:
{json.dumps(reply, indent=2)}

Return JSON: {{"body":"..."}}
"""


def _run_sales_model(prompt: str) -> dict[str, Any]:
    try:
        from tools.growth.score_assessment import run_claude

        return run_claude(prompt)
    except Exception:
        raw = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
        if raw.returncode != 0:
            raise RuntimeError((raw.stderr or raw.stdout).strip()[:300])
        return _json_from_output(raw.stdout)


def _json_from_output(output: str) -> dict[str, Any]:
    start, end = output.find("{"), output.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON in model output")
    return json.loads(output[start : end + 1])


def _touches_from_model(context: LeadContext, raw: dict[str, Any]) -> list[TouchDraft]:
    touches = []
    for index, item in enumerate(raw.get("touches", [])[:4], start=1):
        kind = str(item.get("kind") or TOUCH_KINDS[min(index - 1, len(TOUCH_KINDS) - 1)])
        if kind not in TOUCH_KINDS:
            kind = TOUCH_KINDS[min(index - 1, len(TOUCH_KINDS) - 1)]
        body = with_signature_and_compliance(str(item.get("body") or ""))
        touches.append(
            TouchDraft(
                touch_id=stable_id("touch", context.lead_id, kind, str(index)),
                kind=kind,
                subject=str(item.get("subject") or _default_subject(context, kind)),
                body=body,
                send_after_days=int(item.get("send_after_days") or [0, 2, 5, 8][min(index - 1, 3)]),
                stage_after_send=str(item.get("stage_after_send") or _stage_for_kind(kind)),
            )
        )
    if len(touches) < 4:
        return _fallback_sequence(context)
    return touches


def _fallback_sequence(context: LeadContext) -> list[TouchDraft]:
    first_name = context.name.split()[0] if context.name else "there"
    opp = context.opportunities[0] if context.opportunities else f"the {context.weakest_dimension} bottleneck from your assessment"
    bodies = [
        (
            f"Hi {first_name},\n\nYour assessment points to {opp}. "
            "The useful part is not the score itself. It is choosing one place where better allocation creates proof this week.\n\n"
            "A simple next move: write down the repeated handoff or decision that keeps pulling time away from higher-value work."
        ),
        (
            f"Hi {first_name},\n\nIf it would help, we can use the assessment as the starting map for a short call. "
            "No pressure. The only goal would be to identify the first bottleneck worth turning into a Blueprint."
        ),
        (
            f"Hi {first_name},\n\nThe Blueprint version of this would take the {context.weakest_dimension} constraint, "
            "turn it into an implementation plan, and define the proof that would show the opportunity was captured."
        ),
        (
            f"Hi {first_name},\n\nThe common objection is usually timing, budget, or uncertainty. "
            "That is valid. The assessment should still be useful: make one small allocation change, then compare the result."
        ),
    ]
    subjects = [
        f"Your {context.weakest_dimension} bottleneck is the useful signal",
        "A low-pressure next step from your assessment",
        "What the Blueprint would actually turn into",
        "Useful either way",
    ]
    return [
        TouchDraft(
            touch_id=stable_id("touch", context.lead_id, TOUCH_KINDS[index], str(index + 1)),
            kind=TOUCH_KINDS[index],
            subject=subjects[index],
            body=with_signature_and_compliance(bodies[index]),
            send_after_days=[0, 2, 5, 8][index],
            stage_after_send=["engaged", "booked", "proposed", "proposed"][index],
        )
        for index in range(4)
    ]


def _fallback_reply_body(context: LeadContext, reply: dict[str, Any], inferred_stage: str) -> str:
    first_name = context.name.split()[0] if context.name else "there"
    if inferred_stage == "booked":
        return f"Hi {first_name},\n\nGreat. I saw your note. James should confirm the calendar details and make sure the assessment context is ready before the call."
    if inferred_stage == "proposed":
        return f"Hi {first_name},\n\nGood question. The honest next step is for James to look at your assessment and frame whether the Blueprint is the right fit before talking payment or a close."
    if inferred_stage == "lost":
        return f"Hi {first_name},\n\nThanks for saying so. No pressure. Keep the assessment and use the Monday move as the useful next step."
    return f"Hi {first_name},\n\nThanks for the reply. My read is that the best next step is to look at the {context.weakest_dimension} bottleneck from your assessment and decide whether a Blueprint conversation would be useful."


def _default_subject(context: LeadContext, kind: str) -> str:
    if kind == "soft_booking_cta":
        return "A low-pressure next step from your assessment"
    if kind == "blueprint_offer":
        return "What the Blueprint would actually turn into"
    if kind == "objection_handling":
        return "Useful either way"
    return f"Your {context.weakest_dimension} bottleneck is the useful signal"


def _stage_for_kind(kind: str) -> str:
    return {"value_followup": "engaged", "soft_booking_cta": "booked", "blueprint_offer": "proposed", "objection_handling": "proposed"}.get(kind, "engaged")


def _reply_subject(subject: str) -> str:
    clean = subject.strip() or "your assessment"
    return clean if clean.lower().startswith("re:") else f"Re: {clean}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draft and gate assessment sales follow-up.")
    parser.add_argument("--lead", type=Path, required=True)
    parser.add_argument("--deliverable", type=Path)
    parser.add_argument("--replies", type=Path, help="JSON fixture of inbox replies already read by the inbox layer")
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--write", action="store_true", help="write lane, gates, state, and ledger")
    parser.add_argument("--live", action="store_true", help="allow sending only when SALES_AUTOSEND=1 and a sender is configured")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    plan = plan_for_lead(args.lead, args.deliverable, replies=load_replies(args.replies))
    result = {"plan": plan, "stage_result": None}
    if args.write:
        result["stage_result"] = stage_plan(
            plan,
            lane_path=args.lane,
            queue_path=args.queue,
            state_path=args.state,
            ledger_path=args.ledger,
            live=args.live,
        )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"lead={plan['lead']['lead_id']} sequence={len(plan['sequence'])} "
            f"reply_drafts={len(plan['reply_drafts'])} write={args.write}"
        )
        if result["stage_result"]:
            print(f"lane={result['stage_result']['lane']} gates={len(result['stage_result']['gates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Beacon content variant generation."""
from __future__ import annotations

import json
import os
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from .campaign import BeaconCampaign, BeaconVariant

VOICE_PATH = Path(os.environ.get("BEACON_VOICE_PATH", "core/STATE/identity/VOICE.md"))


def load_voice_context(path: Path = VOICE_PATH) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "Point first. Short sentences. Warm, direct, concise."
    markers = [
        "Point first",
        "Short",
        "Plain English",
        "Lead with",
        "warm",
        "Never sound",
        "Caveman Clarity",
    ]
    lines = []
    for line in text.splitlines():
        clean = line.strip(" -*>\t")
        if clean and any(marker.lower() in clean.lower() for marker in markers):
            lines.append(clean)
        if len(lines) >= 10:
            break
    return " ".join(lines)[:1200] or "Point first. Short sentences. Warm, direct, concise."


def build_prompt(cta_concept: str, audience: str, intent_lane: str, voice_context: str) -> str:
    return (
        "You are writing marketing content in James's voice. "
        f"Voice style: {voice_context}.\n"
        f"Campaign: {cta_concept} | Audience: {audience} | Intent lane: {intent_lane}\n"
        "Every piece must have a trackable link or QR route home - no dead-end content.\n"
        "Generate 3 variants (A/B/C) as JSON: "
        "[{variant_label, content_type, headline, body, cta_text, tone_score, alignment_score}]\n"
        "Be concise. Lead with the hook. Never sound like an ad."
    )


def _run_claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt],
        check=True,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return result.stdout


def _extract_json(text: str) -> list[dict[str, Any]]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("variant JSON must be a list")
    return data


def _fallback_variants(cta_concept: str, audience: str, content_type: str) -> list[dict[str, Any]]:
    return [
        {
            "variant_label": "A",
            "content_type": content_type,
            "headline": cta_concept,
            "body": f"For {audience}: turn attention into a first proof. Start through the Beacon link.",
            "cta_text": "Start through Beacon",
            "tone_score": 0.74,
            "alignment_score": 0.76,
        },
        {
            "variant_label": "B",
            "content_type": content_type,
            "headline": "Your attention can become evidence",
            "body": "A small action is better than another saved idea. Follow the tracked route and make one proof.",
            "cta_text": "Make the first proof",
            "tone_score": 0.72,
            "alignment_score": 0.78,
        },
        {
            "variant_label": "C",
            "content_type": content_type,
            "headline": "What if the next click had to become real?",
            "body": "No dead-end inspiration. Come in, take one clean step, and let the proof speak.",
            "cta_text": "Enter the loop",
            "tone_score": 0.70,
            "alignment_score": 0.75,
        },
    ]


def _coerce_variant(campaign_id: str, intent_lane: str, item: dict[str, Any]) -> BeaconVariant:
    missing = [k for k in ("variant_label", "content_type", "headline", "body", "cta_text") if not item.get(k)]
    if missing:
        raise ValueError(f"variant missing fields: {', '.join(missing)}")
    content_type = str(item["content_type"])
    if content_type == "ad" and os.environ.get("BEACON_PAID_ENABLED") != "1":
        raise PermissionError("content_type=ad requires BEACON_PAID_ENABLED=1")
    return BeaconVariant(
        campaign_id=campaign_id,
        variant_label=str(item["variant_label"]).upper(),
        content_type=content_type,
        headline=str(item["headline"]),
        body=str(item["body"]),
        cta_text=str(item["cta_text"]),
        intent_lane=intent_lane,
        tone_score=Decimal(str(item.get("tone_score", "0"))),
        alignment_score=Decimal(str(item.get("alignment_score", "0"))),
    )


def generate_variants(
    campaign: BeaconCampaign,
    n: int = 3,
    *,
    cta_concept: str | None = None,
    audience: str | None = None,
    intent_lane: str | None = None,
    content_type: str = "post",
    runner: Callable[[str], str] | None = None,
    send_approval: bool = True,
) -> list[BeaconVariant]:
    campaign_id = getattr(campaign, "campaign_id", None) or ""
    if not campaign_id and hasattr(campaign, "store"):
        # create() calls us after computing campaign_id but before attaching it.
        # It passes campaign_id through the temporary attribute below.
        campaign_id = getattr(campaign, "_current_campaign_id", "")
    campaign_id = campaign_id or getattr(campaign, "last_campaign_id", "")
    cta = cta_concept or getattr(campaign, "cta_concept", "Beacon campaign")
    aud = audience or getattr(campaign, "audience", "aligned people")
    lane = intent_lane or getattr(campaign, "intent_lane", "curious")
    voice_context = load_voice_context()
    prompt = build_prompt(cta, aud, lane, voice_context)
    if runner is None and os.environ.get("BEACON_SKIP_CLAUDE") != "1":
        runner = _run_claude
    try:
        rows = _extract_json(runner(prompt)) if runner else _fallback_variants(cta, aud, content_type)
    except Exception:
        rows = _fallback_variants(cta, aud, content_type)
    variants = [_coerce_variant(campaign_id, lane, row) for row in rows[:n]]
    if send_approval:
        send_approval_request(campaign_id, variants)
    return variants


def send_approval_request(campaign_id: str, variants: list[BeaconVariant]) -> bool:
    try:
        import asyncio
        from .. import telegram as tg

        headlines = {v.variant_label: v.headline for v in variants}
        msg = (
            f"Beacon {campaign_id} - 3 variants ready for review.\n"
            f"A: {headlines.get('A', '')}\n"
            f"B: {headlines.get('B', '')}\n"
            f"C: {headlines.get('C', '')}\n"
            f"Reply: b{campaign_id}:A, b{campaign_id}:B, b{campaign_id}:C or b{campaign_id}:all"
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return bool(asyncio.run(tg.send(msg, parse_mode=None)))
        loop.create_task(tg.send(msg, parse_mode=None))
        return True
    except Exception:
        return False

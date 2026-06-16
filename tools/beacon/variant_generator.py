"""Beacon variant generation from approved content-bank source material."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = REPO_ROOT / "docs" / "content_bank"

CAMPAIGN_ASSETS = {
    "A": "02_cora_explainer.md",
    "campaign_a": "02_cora_explainer.md",
    "cora_attention_hook": "02_cora_explainer.md",
    "B": "01_what_is_sunheart_ai.md",
    "campaign_b": "01_what_is_sunheart_ai.md",
    "ai_routing_hook": "01_what_is_sunheart_ai.md",
    "C": "04_camp_zen_explainer.md",
    "campaign_c": "04_camp_zen_explainer.md",
    "camp_zen_proof_hook": "04_camp_zen_explainer.md",
}


@dataclass(frozen=True)
class Variant:
    campaign_id: str
    format_name: str
    source_asset: str
    text: str


def content_asset_for_campaign(campaign_id: str) -> str:
    try:
        return CAMPAIGN_ASSETS[campaign_id]
    except KeyError as exc:
        raise ValueError(f"unknown Beacon campaign: {campaign_id}") from exc


def load_content_bank_asset(campaign_id: str, *, content_dir: Path = CONTENT_DIR) -> tuple[str, str]:
    filename = content_asset_for_campaign(campaign_id)
    path = content_dir / filename
    return filename, path.read_text(encoding="utf-8")


def _clean_source(source: str) -> list[str]:
    lines = []
    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith("[DRAFT") or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def remix_from_content(source: str, format_name: str) -> str:
    lines = _clean_source(source)
    base = " ".join(lines)
    if format_name == "short_video":
        return f"Hook: {base[:220].rstrip()}... CTA: scan, speak, get routed."
    if format_name == "reflection":
        return f"Reflection: {base[:180].rstrip()}... What attention are you ready to turn into proof?"
    if format_name == "chat_onboarding":
        return f"Chat opener: {base[:200].rstrip()}... Tell me what you noticed and I will route the next step."
    return f"{format_name}: {base[:260].rstrip()}..."


def generate_variants(
    campaign_id: str,
    *,
    formats: tuple[str, ...] = ("short_video", "reflection", "chat_onboarding"),
    content_dir: Path = CONTENT_DIR,
) -> list[Variant]:
    source_asset, source = load_content_bank_asset(campaign_id, content_dir=content_dir)
    return [
        Variant(campaign_id=campaign_id, format_name=format_name, source_asset=source_asset, text=remix_from_content(source, format_name))
        for format_name in formats
    ]


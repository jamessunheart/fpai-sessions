from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..config import Settings
from ..models import DeliveryResult, MessageRecord


def target_path(settings: Settings, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now(timezone.utc)).date().isoformat()
    return Path(settings.obsidian_vault) / "FPAI" / "Comms Hub" / f"{stamp}.md"


def deliver(message: MessageRecord, settings: Settings) -> DeliveryResult:
    if not settings.obsidian_enabled:
        return DeliveryResult(status="blocked", detail="COMMS_HUB_OBSIDIAN_ENABLED=0")
    if not settings.obsidian_vault:
        return DeliveryResult(status="blocked", detail="COMMS_HUB_OBSIDIAN_VAULT missing")
    path = target_path(settings)
    if settings.dry_run:
        return DeliveryResult(status="dry_run", detail=f"would append {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {message.created_at} - {message.topic}\n\n{message.body}\n")
    return DeliveryResult(status="delivered", detail=f"appended {path}")

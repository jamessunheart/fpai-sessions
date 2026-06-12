from __future__ import annotations

from ..models import DeliveryResult, MessageRecord


def deliver(message: MessageRecord, dry_run: bool = True) -> DeliveryResult:
    prefix = "[DRY RUN] " if dry_run else ""
    return DeliveryResult(status="dry_run" if dry_run else "delivered", detail=f"{prefix}{message.topic}: {message.body}")

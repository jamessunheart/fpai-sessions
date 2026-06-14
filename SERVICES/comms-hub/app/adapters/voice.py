from __future__ import annotations

from ..config import Settings
from ..models import Attachment, DeliveryResult, MessageInput, MessageRecord


def inbound_voice_message(file_id: str, duration: int, body: str = "[voice message]") -> MessageInput:
    return MessageInput(
        source="telegram",
        audience="system",
        topic="voice",
        body=body,
        attachments=[Attachment(type="voice", file_id=file_id, duration=duration)],
        metadata={"voice_file_id": file_id},
    )


def outbound_voice_reply(message: MessageRecord, settings: Settings) -> DeliveryResult:
    if not settings.voice_enabled:
        return DeliveryResult(status="blocked", detail="COMMS_HUB_VOICE_ENABLED=0")
    if not settings.voice_reply_enabled:
        return DeliveryResult(status="dry_run", detail="voice reply disabled; text fallback")
    if settings.dry_run:
        return DeliveryResult(status="dry_run", detail="would synthesize outbound voice reply")
    return DeliveryResult(status="delivered", detail="voice reply queued")

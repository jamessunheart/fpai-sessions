from __future__ import annotations

from app.adapters import voice
from app.config import Settings
from app.models import MessageInput
from app.store import JsonlStore


def test_inbound_voice_metadata_persists_without_download_in_dry_run(tmp_path):
    store = JsonlStore(tmp_path)
    message = voice.inbound_voice_message("voice-file-1", 9)
    record = store.append_inbox(message)

    assert record.attachments[0].type == "voice"
    assert record.attachments[0].file_id == "voice-file-1"
    assert store.inbox()[0].attachments[0].duration == 9


def test_outbound_voice_reply_is_text_fallback_unless_enabled(tmp_path):
    settings = Settings(var_dir=tmp_path, voice_enabled=True, voice_reply_enabled=False)
    record = JsonlStore(tmp_path).create_record(MessageInput(body="reply"))

    result = voice.outbound_voice_reply(record, settings)

    assert result.status == "dry_run"
    assert "text fallback" in result.detail


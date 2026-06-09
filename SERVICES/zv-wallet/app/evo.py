"""Evolution API client + media fetch."""
from __future__ import annotations
import os
import httpx
from pathlib import Path
from typing import Any

EVO_BASE = os.environ.get("EVO_BASE_URL", "http://127.0.0.1:8081")
EVO_KEY = os.environ.get("EVO_API_KEY", "")
EVO_INSTANCE = os.environ.get("EVO_INSTANCE", "zv-wallet")
MEDIA_DIR = os.environ.get("ZV_WALLET_MEDIA", "/var/lib/zv-wallet/media")


def _headers() -> dict[str, str]:
    return {"apikey": EVO_KEY, "Content-Type": "application/json"}


async def create_instance() -> dict[str, Any]:
    """Idempotent: create the WhatsApp instance for ZV."""
    async with httpx.AsyncClient(timeout=15) as c:
        # Check if exists
        r = await c.get(f"{EVO_BASE}/instance/fetchInstances", headers=_headers())
        if r.status_code == 200:
            data = r.json()
            for inst in (data if isinstance(data, list) else [data]):
                name = inst.get("name") or inst.get("instanceName") or (inst.get("instance", {}) or {}).get("instanceName")
                if name == EVO_INSTANCE:
                    return {"existing": True, "instance": inst}
        # Create
        payload = {
            "instanceName": EVO_INSTANCE,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        r2 = await c.post(f"{EVO_BASE}/instance/create", json=payload, headers=_headers())
        return {"created": True, "response": r2.json() if r2.status_code < 500 else r2.text}


async def get_qr() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{EVO_BASE}/instance/connect/{EVO_INSTANCE}", headers=_headers())
        return r.json() if r.status_code == 200 else {"error": r.status_code, "body": r.text}


async def connection_state() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{EVO_BASE}/instance/connectionState/{EVO_INSTANCE}", headers=_headers())
        return r.json() if r.status_code == 200 else {"error": r.status_code, "body": r.text}


async def send_text(to_phone: str, body: str) -> dict[str, Any]:
    """Send a plain text WhatsApp message. to_phone in E.164 (no +)."""
    phone = to_phone.lstrip("+").replace(" ", "")
    payload = {"number": phone, "text": body}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{EVO_BASE}/message/sendText/{EVO_INSTANCE}",
            json=payload,
            headers=_headers(),
        )
        try:
            return r.json()
        except Exception:
            return {"status": r.status_code, "body": r.text}


async def download_media(message_id: str) -> str | None:
    """Download base64 media via Evolution API. Returns path on disk."""
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{EVO_BASE}/chat/getBase64FromMediaMessage/{EVO_INSTANCE}",
            json={"message": {"key": {"id": message_id}}},
            headers=_headers(),
        )
        if r.status_code != 200:
            return None
        data = r.json()
        b64 = data.get("base64")
        mimetype = data.get("mimetype", "application/octet-stream")
        ext = {
            "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
            "video/mp4": ".mp4", "audio/ogg": ".ogg", "audio/mpeg": ".mp3",
            "audio/wav": ".wav", "application/pdf": ".pdf",
        }.get(mimetype.split(";")[0], "")
        Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
        path = Path(MEDIA_DIR) / f"{message_id}{ext}"
        import base64
        try:
            path.write_bytes(base64.b64decode(b64))
        except Exception:
            return None
        return str(path)


def extract_phone(remote_jid: str) -> str:
    """'5215512345678@s.whatsapp.net' → '5215512345678'."""
    if "@" in remote_jid:
        return remote_jid.split("@", 1)[0]
    return remote_jid

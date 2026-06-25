"""Payment-triggered user activation for Stripe checkout sessions."""
from __future__ import annotations

import importlib.util as _ilu
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping

log = logging.getLogger(__name__)

READY_MESSAGE = "Your agent is ready."


@dataclass(frozen=True)
class PaymentActivationResult:
    user_id: str | None
    namespace: str | None = None
    telegram_chat_id: str | None = None
    telegram_sent: bool = False
    skipped_reason: str | None = None


SendMessage = Callable[..., bool]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path) -> ModuleType:
    spec = _ilu.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = _ilu.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_curator_users() -> ModuleType:
    curator_root = Path(os.environ.get("SUNHEART_BRAIN_CURATOR_ROOT", "")).expanduser()
    if not str(curator_root):
        curator_root = _repo_root() / "SERVICES" / "sunheart-brain" / "curator"
    return _load_module("sunheart_curator_users", curator_root / "users.py")


def _load_hermes_gateway() -> ModuleType:
    curator_root = Path(os.environ.get("SUNHEART_BRAIN_CURATOR_ROOT", "")).expanduser()
    if not str(curator_root):
        curator_root = _repo_root() / "SERVICES" / "sunheart-brain" / "curator"
    return _load_module("sunheart_curator_hermes_gateway", curator_root / "hermes" / "gateway.py")


def _session_metadata(session: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = session.get("metadata") or {}
    return metadata if isinstance(metadata, Mapping) else {}


def extract_user_id(session: Mapping[str, Any]) -> str | None:
    metadata = _session_metadata(session)
    for key in ("user_id", "fpai_user_id", "brain_user_id"):
        value = metadata.get(key)
        if value:
            return str(value)
    client_reference_id = session.get("client_reference_id")
    if client_reference_id:
        return str(client_reference_id)
    return None


def extract_telegram_chat_id(session: Mapping[str, Any]) -> str | None:
    metadata = _session_metadata(session)
    for key in ("telegram_chat_id", "telegram_id", "tg_chat_id", "chat_id"):
        value = metadata.get(key)
        if value:
            return str(value)
    return None


async def activate_paid_checkout_session(
    session: Mapping[str, Any],
    *,
    users_module: ModuleType | Any | None = None,
    send_message: SendMessage | None = None,
) -> PaymentActivationResult:
    """Mark the Stripe payer paid, initialize their namespace, and send TG."""
    user_id = extract_user_id(session)
    if not user_id:
        return PaymentActivationResult(user_id=None, skipped_reason="missing_user_id")

    users = users_module or _load_curator_users()
    activation = await users.activate_paid_user(
        user_id,
        telegram_chat_id=extract_telegram_chat_id(session),
    )
    chat_id = getattr(activation, "telegram_chat_id", None)
    namespace = getattr(activation, "namespace", None)
    if not chat_id:
        return PaymentActivationResult(
            user_id=user_id,
            namespace=namespace,
            skipped_reason="missing_telegram_chat_id",
        )

    sender = send_message
    if sender is None:
        sender = _load_hermes_gateway().send_message
    sent = bool(sender(platform="telegram", handle=str(chat_id), text=READY_MESSAGE))
    if not sent:
        log.warning("paid checkout activation Telegram send failed for user_id=%s", user_id)
    return PaymentActivationResult(
        user_id=user_id,
        namespace=namespace,
        telegram_chat_id=str(chat_id),
        telegram_sent=sent,
        skipped_reason=None if sent else "telegram_send_failed",
    )

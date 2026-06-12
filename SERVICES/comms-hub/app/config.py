from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def env_list(name: str) -> set[str]:
    raw = os.getenv(name, "")
    return {part.strip() for part in raw.split(",") if part.strip()}


@dataclass(frozen=True)
class Settings:
    service_name: str = "comms-hub"
    version: str = "0.1.0"
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])
    var_dir: Path = field(default_factory=lambda: Path(os.getenv("COMMS_HUB_VAR_DIR", Path(__file__).resolve().parents[1] / "var")))
    enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_ENABLED", True))
    dry_run: bool = field(default_factory=lambda: env_bool("COMMS_HUB_DRY_RUN", True))
    outbox_drain_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_OUTBOX_DRAIN_ENABLED", False))
    tg_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_TG_ENABLED", False))
    tg_poll_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_TG_POLL_ENABLED", False))
    tg_send_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_TG_SEND_ENABLED", False))
    obsidian_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_OBSIDIAN_ENABLED", False))
    voice_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_VOICE_ENABLED", False))
    voice_reply_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_VOICE_REPLY_ENABLED", False))
    builder_bridge_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_BUILDER_BRIDGE_ENABLED", False))
    broadcast_enabled: bool = field(default_factory=lambda: env_bool("COMMS_HUB_BROADCAST_ENABLED", False))
    stale_after_seconds: int = field(default_factory=lambda: env_int("COMMS_HUB_STALE_AFTER_SECONDS", 60 * 60 * 24 * 16))
    obsidian_vault: str = field(default_factory=lambda: os.getenv("COMMS_HUB_OBSIDIAN_VAULT", ""))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_allowed_chat_ids: set[str] | None = None

    def __post_init__(self) -> None:
        if self.telegram_allowed_chat_ids is None:
            object.__setattr__(self, "telegram_allowed_chat_ids", env_list("COMMS_HUB_TG_ALLOWED_CHAT_IDS"))
        object.__setattr__(self, "var_dir", Path(self.var_dir))


def load_settings() -> Settings:
    return Settings()

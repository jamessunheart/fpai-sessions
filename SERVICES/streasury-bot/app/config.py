"""app/config.py — typed settings loaded from .env or /etc/streasury-bot/streasury.env."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    """Search a few well-known locations; pydantic merges in order (later wins)."""
    candidates = [
        "/etc/streasury-bot/streasury.env",
        os.environ.get("STREASURY_ENV_FILE", ""),
        str(Path(__file__).resolve().parent.parent / ".env"),
    ]
    return tuple(p for p in candidates if p and Path(p).exists())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    telegram_bot_token: str = ""
    owner_tg_id: int = 0

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o"
    openai_whisper_model: str = "whisper-1"
    ask_default: str = "claude"

    database_url: str = "postgres://streasury:changeme@127.0.0.1:25432/appflowy"

    auto_confirm: bool = False
    default_currency: str = "USD"
    coingecko_base: str = "https://api.coingecko.com/api/v3"

    http_host: str = "0.0.0.0"
    http_port: int = 8620

    log_level: str = "INFO"

    offset_file: str = Field(
        default="/var/lib/streasury-bot/tgbot.offset",
        description="Where to persist Telegram getUpdates offset.",
    )


settings = Settings()

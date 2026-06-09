"""Central configuration. Reads from env; every service inherits."""
from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: str = "development"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://concierge:concierge@localhost:5432/concierge"
    )
    database_url_sync: str = Field(
        default="postgresql://concierge:concierge@localhost:5432/concierge"
    )
    redis_url: str | None = None

    openai_api_key: str | None = None
    openai_realtime_model: str = "gpt-realtime"
    openai_chat_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    grok_api_key: str | None = None
    ollama_url: str | None = None

    deepgram_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_default_voice_id: str | None = None
    openai_tts_voice: str = "alloy"

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_api_key_sid: str | None = None
    twilio_api_key_secret: str | None = None
    twilio_default_from: str | None = None

    apollo_api_key: str | None = None
    hunter_api_key: str | None = None
    hubspot_access_token: str | None = None
    google_calendar_credentials_path: str | None = None

    nerve_center_url: str = "http://198.54.123.234:8120"
    credits_gateway_url: str = "http://198.54.123.234:8765"
    user_service_url: str = "http://198.54.123.234:8110"
    ai_brain_url: str = "http://162.0.208.88:8101"

    tenant_api_url: str = "http://localhost:8820"
    handoff_broker_url: str = "http://localhost:8821"
    voice_router_url: str = "http://localhost:8822"
    outbound_engine_url: str = "http://localhost:8823"
    compliance_gate_url: str = "http://localhost:8824"
    skills_mesh_url: str = "http://localhost:8825"

    tenant_api_port: int = 8820
    handoff_broker_port: int = 8821
    voice_router_port: int = 8822
    outbound_engine_port: int = 8823
    compliance_gate_port: int = 8824
    skills_mesh_port: int = 8825

    public_base_url: str | None = None
    ws_public_base_url: str | None = None

    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    internal_service_token: str = "change-me-in-prod"

    feature_realtime_voice: bool = True
    feature_outbound: bool = False
    feature_skills_mesh: bool = False
    feature_auto_training: bool = True
    feature_ai_qa: bool = True
    feature_conversational_admin: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

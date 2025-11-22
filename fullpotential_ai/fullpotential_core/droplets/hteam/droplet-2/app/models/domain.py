from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Union


class SendMessageRequest(BaseModel):
    """Request model for sending messages to other droplets"""
    target: Union[int, str]  # droplet_id_or_name per UDC spec
    message_type: Literal["status", "event", "command", "query"] = "event"
    payload: Dict[Any, Any] = {}
    priority: Literal["high", "normal", "low"] = "normal"
    retry_count: int = Field(3, ge=0, le=10)


class ReloadConfigRequest(BaseModel):
    """Request model for config reload"""
    config_path: str = "/config/droplet.json"


class ShutdownRequest(BaseModel):
    """Request model for graceful shutdown"""
    delay_seconds: int = Field(10, ge=0, le=300)
    reason: str = "maintenance"
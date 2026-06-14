"""Configuration for intent-queue service"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "intent-queue"
    service_port: int = 8212
    service_host: str = "0.0.0.0"
    service_version: str = "1.0.0"
    tier: int = 0
    
    registry_url: str = "http://localhost:8000"
    governance_url: str = "http://localhost:8213"
    
    max_queue_size: int = 1000
    
    class Config:
        env_file = ".env"

settings = Settings()

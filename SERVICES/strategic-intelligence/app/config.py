from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    service_name: str = "strategic-intelligence"
    service_port: int = 8500
    service_version: str = "1.0.0"
    
    # Paths
    base_path: Path = Path("/Users/jamessunheart/FPAI_Cockpit")
    coordination_path: Path = base_path / "docs/coordination"
    intents_path: Path = coordination_path / "intents"
    ssot_path: Path = coordination_path / "SSOT.json"
    
    # Registry
    registry_url: str = "http://localhost:8000"
    
    # Monitoring
    monitor_interval_seconds: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()


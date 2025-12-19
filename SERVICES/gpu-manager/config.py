"""
GPU Manager Configuration - SINGLE SOURCE OF TRUTH
==================================================

ALL GPU-related settings in ONE place. No more conflicting configs.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class BudgetConfig(BaseModel):
    """Budget limits - HARD ENFORCED"""
    
    # Daily spending limit - ABSOLUTE MAXIMUM
    daily_hard_limit_usd: float = Field(
        default=20.0,
        description="HARD STOP - Never exceed this. System shuts down all GPUs if breached."
    )
    
    # Soft limit for alerts
    daily_soft_limit_usd: float = Field(
        default=15.0,
        description="Alert threshold - warn but don't stop"
    )
    
    # Per-GPU cost thresholds
    max_gpu_hourly_cost: float = Field(
        default=0.10,
        description="Never rent a GPU more expensive than this"
    )
    
    bargain_gpu_hourly_cost: float = Field(
        default=0.05,
        description="GPUs below this are considered bargains"
    )


class ScalingConfig(BaseModel):
    """Scaling rules - CONSERVATIVE BY DEFAULT"""
    
    # GPU count limits
    min_gpus: int = Field(default=0, description="Minimum GPUs to keep (0 = can scale to zero)")
    max_gpus: int = Field(default=10, description="Maximum GPUs allowed")
    
    # Utilization thresholds
    scale_up_utilization: float = Field(
        default=70.0,
        description="Scale UP when utilization exceeds this %"
    )
    scale_down_utilization: float = Field(
        default=20.0,
        description="Scale DOWN when utilization below this %"
    )
    
    # Idle detection
    idle_minutes: int = Field(
        default=15,
        description="Consider GPU idle after this many minutes of low utilization"
    )
    
    # Scale timing
    scale_up_cooldown_minutes: int = Field(
        default=10,
        description="Wait this long between scale-up actions"
    )
    scale_down_cooldown_minutes: int = Field(
        default=5,
        description="Wait this long between scale-down actions (faster than up)"
    )


class MonitoringConfig(BaseModel):
    """Monitoring settings"""
    
    # Check interval
    check_interval_seconds: int = Field(
        default=60,
        description="How often to check utilization (1 minute)"
    )
    
    # Endpoints to monitor for utilization
    utilization_endpoints: list = Field(
        default=[
            "http://162.0.208.88:8400/stats",  # GPU Bridge on secondary server
            "http://162.0.208.88:8101/stats",  # AI Brain
        ],
        description="Endpoints to check for GPU utilization"
    )
    
    # Fallback: If no utilization data, assume idle
    assume_idle_on_no_data: bool = Field(
        default=True,
        description="If can't get utilization, assume idle and scale down"
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breakers - SAFETY FIRST"""
    
    # Emergency stop conditions
    emergency_stop_daily_cost: float = Field(
        default=25.0,
        description="EMERGENCY: Destroy ALL instances if daily cost exceeds this"
    )
    
    emergency_stop_gpu_count: int = Field(
        default=15,
        description="EMERGENCY: Destroy excess if GPU count exceeds this"
    )
    
    # Anomaly detection
    max_gpus_per_hour: int = Field(
        default=3,
        description="Max GPUs that can be created in one hour"
    )
    
    # Lock file to prevent runaway
    lock_file: Path = Field(
        default=Path("/tmp/gpu_manager.lock"),
        description="Lock file to prevent multiple instances"
    )


class VastAIConfig(BaseModel):
    """Vast.ai API configuration"""
    
    api_key: str = Field(
        default="",
        description="Vast.ai API key - loaded from environment"
    )
    
    api_base_url: str = Field(
        default="https://console.vast.ai/api/v0",
        description="Vast.ai API base URL"
    )
    
    # GPU preferences
    preferred_gpu_types: list = Field(
        default=["RTX 3070", "RTX 3060", "GTX 1080 Ti", "RTX 2070"],
        description="Preferred GPU types in order"
    )
    
    min_vram_gb: int = Field(default=8, description="Minimum VRAM required")
    min_disk_gb: int = Field(default=20, description="Minimum disk space")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Load API key from environment
        self.api_key = os.environ.get("VASTAI_API_KEY", "")


class GPUManagerConfig(BaseModel):
    """Master configuration - ALL SETTINGS IN ONE PLACE"""
    
    # Enable/disable the manager
    enabled: bool = Field(
        default=False,  # DISABLED BY DEFAULT - must explicitly enable
        description="Master switch - set to True to enable GPU management"
    )
    
    # Mode
    mode: str = Field(
        default="monitor_only",  # Safe default
        description="Mode: 'monitor_only', 'scale_down_only', 'full_auto'"
    )
    
    # Sub-configs
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    scaling: ScalingConfig = Field(default_factory=ScalingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    vastai: VastAIConfig = Field(default_factory=VastAIConfig)
    
    # Logging
    log_file: Path = Field(
        default=Path("/var/log/gpu_manager.log"),
        description="Log file location"
    )
    
    # State file
    state_file: Path = Field(
        default=Path("/var/log/gpu_manager_state.json"),
        description="State file for persistence"
    )


def load_config() -> GPUManagerConfig:
    """Load configuration with environment overrides"""
    config = GPUManagerConfig()
    
    # Override from environment
    if os.environ.get("GPU_MANAGER_ENABLED", "").lower() == "true":
        config.enabled = True
    
    if os.environ.get("GPU_MANAGER_MODE"):
        config.mode = os.environ.get("GPU_MANAGER_MODE")
    
    if os.environ.get("GPU_DAILY_BUDGET"):
        config.budget.daily_hard_limit_usd = float(os.environ.get("GPU_DAILY_BUDGET"))
    
    if os.environ.get("GPU_MAX_COUNT"):
        config.scaling.max_gpus = int(os.environ.get("GPU_MAX_COUNT"))
    
    return config


# Default instance
config = load_config()

"""
Configuration Management
Centralized settings using pydantic-settings
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    app_name: str = Field("Orchestrator", description="Application name")
    app_version: str = Field("2.0.0", description="Application version")
    environment: str = Field("development", description="Environment (development/staging/production)")
    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")
    
    # ========================================================================
    # SERVER
    # ========================================================================
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    workers: int = Field(4, description="Number of Uvicorn workers")
    reload: bool = Field(False, description="Auto-reload on code changes")
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string",
        json_schema_extra={"env": "DATABASE_URL"}
    )
    db_pool_size: int = Field(20, description="Database connection pool size")
    db_max_overflow: int = Field(10, description="Max database connection overflow")
    db_pool_timeout: int = Field(30, description="Database pool timeout (seconds)")
    
    # ========================================================================
    # REGISTRY INTEGRATION
    # ========================================================================
    registry_url: str = Field(
        "https://registry.fullpotential.ai",
        description="Registry droplet endpoint"
    )
    registry_sync_interval: int = Field(
        300,
        description="Seconds between directory syncs"
    )
    registry_timeout: int = Field(5, description="Registry HTTP timeout (seconds)")
    
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    
    jwt_algorithm: str = Field("RS256", description="JWT algorithm (RS256 recommended)")
    jwt_secret_key: str = Field(       
        ...,
        description="confirmation secret key",
        json_schema_extra={"env": "JWT_SECRET_KEY"}
    )
    # Public key for verifying incoming JWTs (required)
    jwt_public_key: str = Field(
        ...,
        description="RSA public key (PEM) used to verify JWT signatures",
        json_schema_extra={"env": "JWT_PUBLIC_KEY"}
    )

    # Private key for signing outgoing JWTs (optional)
    jwt_private_key: Optional[str] = Field(
        None,
        description="RSA private key (PEM) used for signing JWTs",
        json_schema_extra={"env": "JWT_PRIVATE_KEY"}
    )

    jwt_expiration: int = Field(86400, description="Token expiration (seconds)")

    registry_public_key_url: Optional[str] = Field(
        None,
        description="URL to fetch registry public key automatically"
    )
    
    # ========================================================================
    # DROPLET IDENTITY
    # ========================================================================
    droplet_id: int = Field(10, description="This droplet's ID")
    droplet_name: str = Field("Orchestrator", description="This droplet's name")
    droplet_steward: str = Field("Tnsae", description="Droplet steward")
    droplet_endpoint: str = Field(
        "https://orchestrator.fullpotential.ai",
        description="This droplet's public endpoint"
    )
    
    # ========================================================================
    # HEALTH MONITORING
    # ========================================================================
    heartbeat_check_interval: int = Field(
        60,
        description="Seconds between droplet health checks"
    )
    heartbeat_timeout: int = Field(
        90,
        description="Mark droplet inactive after this many seconds"
    )
    heartbeat_retention: int = Field(
        86400,
        description="Keep heartbeat records for this many seconds (24h)"
    )
    
    # ========================================================================
    # TASK MANAGEMENT
    # ========================================================================
    task_assignment_timeout: int = Field(
        10,
        description="Seconds to wait for task assignment"
    )
    task_default_max_retries: int = Field(3, description="Default max retries")
    task_retention_days: int = Field(90, description="Keep completed tasks for N days")
    
    # ========================================================================
    # WEBSOCKET
    # ========================================================================
    ws_heartbeat_interval: int = Field(30, description="WebSocket ping interval")
    ws_max_connections: int = Field(1000, description="Max concurrent WebSocket connections")
    
    # ========================================================================
    # REDIS (Optional)
    # ========================================================================
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    redis_max_connections: int = Field(50, description="Max Redis connections")
    
    # ========================================================================
    # CORS
    # ========================================================================
    cors_origins: List[str] = Field(
        default_factory=lambda: ["https://dashboard.fullpotential.ai", "http://localhost:3000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(True, description="Allow CORS credentials")
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    rate_limit_per_minute: int = Field(100, description="Max requests per IP per minute")
    rate_limit_burst: int = Field(20, description="Rate limit burst allowance")
    
    # ========================================================================
    # METRICS & MONITORING
    # ========================================================================
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    metrics_port: int = Field(9090, description="Prometheus metrics port")
    
    # ========================================================================
    # PERFORMANCE
    # ========================================================================
    request_timeout: int = Field(30, description="HTTP request timeout (seconds)")
    slow_query_threshold: float = Field(1.0, description="Log queries slower than this (seconds)")
    
    # ========================================================================
    # SECURITY
    # ========================================================================
    ssl_certfile: Optional[str] = Field(None, description="SSL certificate file path")
    ssl_keyfile: Optional[str] = Field(None, description="SSL key file path")
    forwarded_allow_ips: str = Field("*", description="Trusted proxy IPs")
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    enable_auto_recovery: bool = Field(True, description="Automatic task reassignment")
    enable_task_prioritization: bool = Field(True, description="Priority-based routing")
    enable_metrics_collection: bool = Field(True, description="Collect performance metrics")
    
    # ========================================================================
    # TESTING
    # ========================================================================
    test_database_url: Optional[str] = Field(
        None,
        description="Test database URL"
    )
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins from environment"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Ensure environment is valid"""
        valid_envs = {'development', 'staging', 'production'}
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v_lower
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra env vars
    )
    
    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for migrations)"""
        return self.database_url.replace('+asyncpg', '')
    
    @property
    def enable_swagger(self) -> bool:
        """Enable Swagger UI only in development"""
        return self.is_development or self.debug


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Use this function to access settings throughout the application
    """
    return Settings()


# ============================================================================
# CONVENIENCE EXPORTS
# ============================================================================

settings = get_settings()

# Log configuration on startup
if settings.is_development:
    import json
    print("=" * 80)
    print("ORCHESTRATOR CONFIGURATION")
    print("=" * 80)
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")
    print(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    print(f"Registry: {settings.registry_url}")
    print(f"Droplet ID: {settings.droplet_id}")
    print(f"Droplet Endpoint: {settings.droplet_endpoint}")
    print("=" * 80)
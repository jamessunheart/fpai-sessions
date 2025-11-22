"""Generation Models for SPEC Builder"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ServiceType(str, Enum):
    """Service type"""
    INFRASTRUCTURE = "infrastructure"
    SACRED_LOOP = "sacred_loop"
    DOMAIN = "domain"
    API_GATEWAY = "api_gateway"
    DATA = "data"


class GenerateRequest(BaseModel):
    """Request to generate SPEC from intent"""
    service_name: str = Field(..., description="Service name (kebab-case)")
    service_type: ServiceType = Field(..., description="Type of service")
    purpose: str = Field(..., description="What this service does")
    key_features: List[str] = Field(
        default_factory=list,
        description="Main features of the service"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Required dependencies"
    )
    port: int = Field(..., ge=1024, le=65535, description="Service port")
    tier: Optional[int] = Field(None, ge=0, le=4, description="TIER level (0-4)")
    auto_optimize: bool = Field(True, description="Auto-optimize after generation")
    target_score: int = Field(90, ge=0, le=100, description="Target quality score")


class GenerateFromTemplateRequest(BaseModel):
    """Request to generate SPEC from template"""
    template: str = Field(..., description="Template name")
    service_name: str = Field(..., description="Service name")
    purpose: str = Field(..., description="Service purpose")
    customizations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template customizations"
    )


class RefineRequest(BaseModel):
    """Request to refine existing SPEC"""
    spec_content: str = Field(..., description="Existing SPEC content")
    additional_requirements: List[str] = Field(
        ...,
        description="Additional requirements to add"
    )


class InteractiveRequest(BaseModel):
    """Interactive SPEC generation request"""
    session_id: Optional[str] = Field(None, description="Session ID")
    message: str = Field(..., description="User message")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Session context"
    )


class GenerationResult(BaseModel):
    """SPEC generation result"""
    success: bool
    spec_content: str
    verification: Optional[Dict[str, Any]] = None
    optimized: bool = False
    final_score: float = 0.0
    improvements: List[str] = Field(default_factory=list)
    claude_cost_usd: float = 0.0
    generation_time_seconds: float = 0.0
    error: Optional[str] = None


class InteractiveResponse(BaseModel):
    """Interactive session response"""
    session_id: str
    response: str
    ready_to_generate: bool
    context_updated: bool


class TemplateInfo(BaseModel):
    """Template information"""
    name: str
    description: str
    examples: List[str]

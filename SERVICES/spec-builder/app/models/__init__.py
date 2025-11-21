"""Models for SPEC Builder"""

from .udc_models import (
    UDCHealthResponse,
    UDCCapabilitiesResponse,
    UDCStateResponse,
    UDCDependenciesResponse,
    DependencyStatus,
    UDCMessageRequest,
    UDCMessageResponse
)

from .generation_models import (
    ServiceType,
    GenerateRequest,
    GenerateFromTemplateRequest,
    RefineRequest,
    InteractiveRequest,
    GenerationResult,
    InteractiveResponse,
    TemplateInfo
)

__all__ = [
    "UDCHealthResponse",
    "UDCCapabilitiesResponse",
    "UDCStateResponse",
    "UDCDependenciesResponse",
    "DependencyStatus",
    "UDCMessageRequest",
    "UDCMessageResponse",
    "ServiceType",
    "GenerateRequest",
    "GenerateFromTemplateRequest",
    "RefineRequest",
    "InteractiveRequest",
    "GenerationResult",
    "InteractiveResponse",
    "TemplateInfo"
]

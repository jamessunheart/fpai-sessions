"""Models for SPEC Optimizer"""

from .udc_models import (
    UDCHealthResponse,
    UDCCapabilitiesResponse,
    UDCStateResponse,
    UDCDependenciesResponse,
    DependencyStatus,
    UDCMessageRequest,
    UDCMessageResponse
)

from .optimization_models import (
    OptimizationLevel,
    OptimizeRequest,
    OptimizeFileRequest,
    BatchOptimizeRequest,
    VerificationSnapshot,
    OptimizationResult,
    BatchOptimizationResult
)

__all__ = [
    "UDCHealthResponse",
    "UDCCapabilitiesResponse",
    "UDCStateResponse",
    "UDCDependenciesResponse",
    "DependencyStatus",
    "UDCMessageRequest",
    "UDCMessageResponse",
    "OptimizationLevel",
    "OptimizeRequest",
    "OptimizeFileRequest",
    "BatchOptimizeRequest",
    "VerificationSnapshot",
    "OptimizationResult",
    "BatchOptimizationResult"
]

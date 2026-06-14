"""Models for SPEC Verifier"""

from .udc_models import (
    UDCHealthResponse,
    UDCCapabilitiesResponse,
    UDCStateResponse,
    UDCDependenciesResponse,
    DependencyStatus,
    UDCMessageRequest,
    UDCMessageResponse
)

from .verification_models import (
    VerifyRequest,
    VerifyFileRequest,
    VerificationScore,
    VerificationSections,
    UDCEndpointCheck,
    VerificationResult,
    ReferenceSpec,
    CompareRequest,
    ComparisonResult
)

__all__ = [
    "UDCHealthResponse",
    "UDCCapabilitiesResponse",
    "UDCStateResponse",
    "UDCDependenciesResponse",
    "DependencyStatus",
    "UDCMessageRequest",
    "UDCMessageResponse",
    "VerifyRequest",
    "VerifyFileRequest",
    "VerificationScore",
    "VerificationSections",
    "UDCEndpointCheck",
    "VerificationResult",
    "ReferenceSpec",
    "CompareRequest",
    "ComparisonResult"
]

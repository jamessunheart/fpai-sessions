"""Verification Models for SPEC Verifier"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class VerifyRequest(BaseModel):
    """Request to verify SPEC content"""
    spec_content: str = Field(..., description="SPEC markdown content")
    spec_path: Optional[str] = Field(None, description="Optional path to SPEC file")
    strict_mode: bool = Field(False, description="Enable strict validation")


class VerifyFileRequest(BaseModel):
    """Request to verify SPEC file by path"""
    file_path: str = Field(..., description="Absolute path to SPEC.md file")
    strict_mode: bool = Field(False, description="Enable strict validation")


class VerificationScore(BaseModel):
    """SPEC quality scores"""
    completeness: int = Field(..., ge=0, le=100, description="Completeness score (0-100)")
    clarity: int = Field(..., ge=0, le=100, description="Clarity score (0-100)")
    udc_compliance: int = Field(..., ge=0, le=100, description="UDC compliance score (0-100)")
    build_readiness: int = Field(..., ge=0, le=100, description="Build readiness score (0-100)")
    overall: float = Field(..., ge=0, le=100, description="Overall weighted score")


class VerificationSections(BaseModel):
    """SPEC sections analysis"""
    found: List[str] = Field(default_factory=list, description="Sections found in SPEC")
    missing: List[str] = Field(default_factory=list, description="Required sections missing")
    incomplete: List[str] = Field(default_factory=list, description="Sections present but incomplete")


class UDCEndpointCheck(BaseModel):
    """UDC endpoint documentation check"""
    documented: int = Field(..., description="Number of endpoints documented")
    required: int = Field(5, description="Number of required endpoints")
    missing: List[str] = Field(default_factory=list, description="Missing endpoints")
    compliant: bool = Field(..., description="Whether UDC compliant")


class VerificationResult(BaseModel):
    """Complete SPEC verification result"""
    valid: bool = Field(..., description="Whether SPEC is valid")
    score: VerificationScore = Field(..., description="Quality scores")
    sections: VerificationSections = Field(..., description="Sections analysis")
    udc_endpoints: UDCEndpointCheck = Field(..., description="UDC endpoint check")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    errors: List[str] = Field(default_factory=list, description="Critical errors")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")


class ReferenceSpec(BaseModel):
    """Reference SPEC metadata"""
    name: str
    path: str
    tier: int
    score: Optional[float] = None


class CompareRequest(BaseModel):
    """Request to compare SPEC against references"""
    spec_content: Optional[str] = Field(None, description="SPEC markdown content")
    spec_path: Optional[str] = Field(None, description="Path to SPEC file")
    compare_with: List[str] = Field(
        default_factory=list,
        description="List of reference spec names to compare against"
    )


class ComparisonResult(BaseModel):
    """SPEC comparison result"""
    similarities: List[str] = Field(default_factory=list, description="Similarities with references")
    differences: List[str] = Field(default_factory=list, description="Differences from references")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations based on comparison")
    reference_scores: Dict[str, float] = Field(default_factory=dict, description="Scores of reference specs")

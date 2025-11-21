"""Optimization Models for SPEC Optimizer"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class OptimizationLevel(str, Enum):
    """Optimization level"""
    BASIC = "basic"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


class OptimizeRequest(BaseModel):
    """Request to optimize SPEC content"""
    spec_content: str = Field(..., description="SPEC markdown content")
    spec_path: Optional[str] = Field(None, description="Optional path to SPEC file")
    optimization_level: OptimizationLevel = Field(
        OptimizationLevel.STANDARD,
        description="Optimization level"
    )
    preserve_sections: List[str] = Field(
        default_factory=list,
        description="Sections to preserve as-is"
    )
    target_score: int = Field(
        85,
        ge=0,
        le=100,
        description="Target quality score"
    )


class OptimizeFileRequest(BaseModel):
    """Request to optimize SPEC file by path"""
    file_path: str = Field(..., description="Absolute path to SPEC.md file")
    optimization_level: OptimizationLevel = Field(
        OptimizationLevel.STANDARD,
        description="Optimization level"
    )
    save_backup: bool = Field(True, description="Save backup of original")
    overwrite: bool = Field(False, description="Overwrite original file")


class BatchOptimizeRequest(BaseModel):
    """Request to optimize multiple SPEC files"""
    file_paths: List[str] = Field(..., description="List of SPEC file paths")
    optimization_level: OptimizationLevel = Field(
        OptimizationLevel.STANDARD,
        description="Optimization level for all files"
    )


class VerificationSnapshot(BaseModel):
    """SPEC verification snapshot"""
    score: Dict[str, float] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    """Complete optimization result"""
    success: bool
    original_spec: str
    optimized_spec: str
    verification_before: VerificationSnapshot
    verification_after: VerificationSnapshot
    improvements: List[str] = Field(default_factory=list)
    score_improvement: float
    claude_cost_usd: float
    input_tokens: int = 0
    output_tokens: int = 0
    backup_path: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class BatchOptimizationResult(BaseModel):
    """Batch optimization result"""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total_improved: int
    total_failed: int
    average_improvement: float
    total_cost_usd: float

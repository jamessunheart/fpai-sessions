"""
LEVEL 10 INTELLIGENCE SYSTEM
==============================

The Five Pillars of True Intelligence:

1. REAL VERIFICATION - Test actual functionality, not just health endpoints
2. ROOT CAUSE ANALYSIS - Ask WHY, not just WHAT
3. LEARNING MEMORY - Remember failures and what fixed them
4. SELF-CORRECTION - Fix with verification and learning
5. META-LEARNING - Learn to learn better

This transforms Aria from reactive (4/10) to truly intelligent (10/10).
"""

from .intelligence_db import IntelligenceDB, get_intelligence_db
from .real_verification import RealVerifier, VerificationResult, get_verifier
from .config_contracts import ConfigContract, ConfigDrift, get_config_contract
from .root_cause import RootCauseAnalyzer, RootCause, get_root_cause_analyzer
from .failure_memory import FailureMemory, HistoricalFailure, Fix, get_failure_memory
from .intelligent_healer import IntelligentHealer, HealResult, get_intelligent_healer
from .pattern_engine import PatternEngine, Pattern, Prediction, get_pattern_engine
from .meta_learning import MetaLearner, LearningMetrics, get_meta_learner

__all__ = [
    # Database
    "IntelligenceDB",
    "get_intelligence_db",
    
    # Real Verification
    "RealVerifier",
    "VerificationResult",
    "get_verifier",
    
    # Config Contracts
    "ConfigContract",
    "ConfigDrift",
    "get_config_contract",
    
    # Root Cause Analysis
    "RootCauseAnalyzer",
    "RootCause",
    "get_root_cause_analyzer",
    
    # Failure Memory
    "FailureMemory",
    "HistoricalFailure",
    "Fix",
    "get_failure_memory",
    
    # Intelligent Healer
    "IntelligentHealer",
    "HealResult",
    "get_intelligent_healer",
    
    # Pattern Engine
    "PatternEngine",
    "Pattern",
    "Prediction",
    "get_pattern_engine",
    
    # Meta Learning
    "MetaLearner",
    "LearningMetrics",
    "get_meta_learner",
]










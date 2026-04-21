"""
SEWA - Sepsis Early Warning Agent

Hybrid intelligence system for early sepsis detection combining:
- Statistical trend analysis
- Machine learning risk scoring  
- Rule-based clinical safety
- LLM-powered explanations

Version: 1.0
"""

__version__ = "1.0.0"
__author__ = "SEWA Development Team"

from .trend_engine import TrendRecognitionEngine, VitalSign
from .data_generator import SyntheticCohortGenerator, PatientTrajectory, RiskLevel
from .ml_pipeline import SEWARiskModel, FeatureExtractor
from .core_system import (
    SEWASystem,
    PatientState,
    SEWAAlert,
    ClinicalRuleEngine,
    AlertAction,
    RiskLevel
)

__all__ = [
    # Core components
    'SEWASystem',
    'TrendRecognitionEngine',
    'SEWARiskModel',
    'ClinicalRuleEngine',
    
    # Data structures
    'PatientState',
    'SEWAAlert',
    'VitalSign',
    
    # Enums
    'RiskLevel',
    'AlertAction',
    
    # Data generation
    'SyntheticCohortGenerator',
    'PatientTrajectory',
    'FeatureExtractor',
]
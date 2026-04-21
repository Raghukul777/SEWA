"""
SEWA - Sepsis Early Warning Agent
Artifact 4: Full Integration System (Simplified)

Complete SEWA system integrating all components with
simplified, production-ready code.

Author: SEWA Development Team
Version: 1.0
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum


# ========== ENUMS ==========

class RiskLevel(IntEnum):
    """Risk stratification levels."""
    NO_RISK = 0
    WATCH = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class AlertAction(IntEnum):
    """Recommended clinical actions."""
    NONE = 0
    MONITOR = 1
    ESCALATE = 2
    RAPID_RESPONSE = 3
    EMERGENCY = 4


# ========== DATA STRUCTURES ==========

@dataclass
class PatientState:
    """Current patient vital signs."""
    timestamp: datetime
    lactate: Optional[float] = None
    map: Optional[float] = None
    hr: Optional[float] = None
    temp: Optional[float] = None
    rr: Optional[float] = None
    spo2: Optional[float] = None
    on_vasopressors: bool = False
    infection_suspected: bool = False


@dataclass
class SEWAAlert:
    """Complete SEWA alert with all context."""
    patient_id: str
    timestamp: datetime
    ml_risk_level: RiskLevel
    final_risk_level: RiskLevel
    risk_score: float
    rules_triggered: List[str]
    override_applied: bool
    override_reason: Optional[str]
    key_trends: List[str]
    concerning_vitals: List[str]
    recommended_action: AlertAction
    clinical_narrative: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'patient_id': self.patient_id,
            'timestamp': self.timestamp.isoformat(),
            'ml_risk_level': self.ml_risk_level.name,
            'final_risk_level': self.final_risk_level.name,
            'risk_score': self.risk_score,
            'rules_triggered': self.rules_triggered,
            'override_applied': self.override_applied,
            'override_reason': self.override_reason,
            'key_trends': self.key_trends,
            'concerning_vitals': self.concerning_vitals,
            'recommended_action': self.recommended_action.name,
            'clinical_narrative': self.clinical_narrative
        }


# ========== RULE ENGINE ==========

class ClinicalRuleEngine:
    """Rule-based safety layer that overrides ML when needed."""
    
    THRESHOLDS = {
        'lactate_critical': 4.0,
        'lactate_high': 2.0,
        'map_critical': 55,
        'map_hypotensive': 65,
        'hr_severe': 120,
        'temp_fever': 38.0,
        'rr_tachypnea': 22,
        'spo2_hypoxia': 92,
    }
    
    def evaluate(self, patient_state: PatientState, 
                 features: Dict, ml_risk: RiskLevel) -> Tuple[RiskLevel, List[str], Optional[str]]:
        """
        Apply clinical rules to override ML if needed.
        
        Returns: (final_risk, rules_triggered, override_reason)
        """
        rules = []
        reason = None
        risk = ml_risk
        
        # Rule 1: Severe hypotension + lactate
        if (patient_state.map and patient_state.lactate and
            patient_state.map < self.THRESHOLDS['map_critical'] and
            patient_state.lactate > self.THRESHOLDS['lactate_high']):
            rules.append('SEVERE_HYPOTENSION_LACTATE')
            if risk < RiskLevel.CRITICAL:
                risk = RiskLevel.CRITICAL
                reason = "Severe hypotension with elevated lactate"
        
        # Rule 2: Critical lactate
        if patient_state.lactate and patient_state.lactate > self.THRESHOLDS['lactate_critical']:
            rules.append('CRITICAL_LACTATE')
            if risk < RiskLevel.HIGH:
                risk = RiskLevel.HIGH
                reason = "Lactate >4.0 mmol/L"
        
        # Rule 3: Vasopressor escalation
        if patient_state.on_vasopressors and ml_risk >= RiskLevel.MODERATE:
            rules.append('VASOPRESSOR_ESCALATION')
            if risk < RiskLevel.HIGH:
                risk = RiskLevel.HIGH
                reason = "Patient on vasopressors"
        
        # Rule 4: Rapid lactate rise
        lactate_slope = features.get('lactate_slope_short', 0)
        if lactate_slope and lactate_slope > 0.8:
            rules.append('RAPID_LACTATE_RISE')
            if risk < RiskLevel.MODERATE:
                risk = RiskLevel.MODERATE
                reason = "Rapidly rising lactate"
        
        # Rule 5: Multi-organ dysfunction
        dysfunction = sum([
            patient_state.lactate and patient_state.lactate > self.THRESHOLDS['lactate_high'],
            patient_state.map and patient_state.map < self.THRESHOLDS['map_hypotensive'],
            patient_state.rr and patient_state.rr > self.THRESHOLDS['rr_tachypnea'],
            patient_state.spo2 and patient_state.spo2 < self.THRESHOLDS['spo2_hypoxia']
        ])
        if dysfunction >= 2:
            rules.append('MULTI_ORGAN_DYSFUNCTION')
            if risk < RiskLevel.MODERATE:
                risk = RiskLevel.MODERATE
                reason = "Multiple organ dysfunction"
        
        # Rule 6: SIRS with infection
        if patient_state.infection_suspected:
            sirs = sum([
                patient_state.temp and (patient_state.temp > 38.0 or patient_state.temp < 36.0),
                patient_state.hr and patient_state.hr > 90,
                patient_state.rr and patient_state.rr > 20
            ])
            if sirs >= 2:
                rules.append('SIRS_WITH_INFECTION')
                if risk < RiskLevel.WATCH:
                    risk = RiskLevel.WATCH
                    reason = "SIRS with infection"
        
        return risk, rules, reason
    
    def get_action(self, risk: RiskLevel, rules: List[str]) -> AlertAction:
        """Map risk level to clinical action."""
        if 'SEVERE_HYPOTENSION_LACTATE' in rules:
            return AlertAction.EMERGENCY
        
        action_map = {
            RiskLevel.NO_RISK: AlertAction.NONE,
            RiskLevel.WATCH: AlertAction.MONITOR,
            RiskLevel.MODERATE: AlertAction.ESCALATE,
            RiskLevel.HIGH: AlertAction.RAPID_RESPONSE,
            RiskLevel.CRITICAL: AlertAction.EMERGENCY
        }
        return action_map.get(risk, AlertAction.NONE)


# ========== LLM EXPLAINER ==========

class ExplanationGenerator:
    """Generates clinical narratives using Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini client."""
        import os
        import google.generativeai as genai
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.use_llm = True
        else:
            self.model = None
            self.use_llm = False
    
    def generate(self, alert: SEWAAlert, patient_state: PatientState) -> str:
        """Generate explanation for alert."""
        # If no API key, use template
        if not self.use_llm:
            return self._generate_template(alert)
        
        # Build prompt for Gemini
        prompt = f"""You are SEWA, a clinical AI system for sepsis detection.

Generate a concise clinical narrative (2-3 sentences) for ICU staff.

Patient Alert:
- Risk Level: {alert.final_risk_level.name}
- Risk Score: {alert.risk_score:.2f}
- Trends: {', '.join(alert.key_trends) if alert.key_trends else 'None'}
- Concerning Vitals: {', '.join(alert.concerning_vitals) if alert.concerning_vitals else 'None'}
- Rules Triggered: {', '.join(alert.rules_triggered) if alert.rules_triggered else 'None'}
- Override: {alert.override_applied}

Focus on:
1. What temporal patterns were detected
2. Why this alert level was chosen
3. What clinical actions are recommended

Be direct, clinical, and actionable. Avoid hedging language."""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"LLM API error: {e}, falling back to template")
            return self._generate_template(alert)
    
    def _generate_template(self, alert: SEWAAlert) -> str:
        """Template-based fallback."""
        risk = alert.final_risk_level.name
        trends = alert.key_trends
        
        if risk == 'CRITICAL':
            return f"CRITICAL sepsis risk. {' '.join(trends[:2])} Severe hemodynamic instability. Immediate physician evaluation required."
        elif risk == 'HIGH':
            return f"HIGH sepsis risk. {' '.join(trends[:2])} Multiple organ dysfunction indicators present. Recommend rapid response team."
        elif risk == 'MODERATE':
            return f"MODERATE sepsis concern. {' '.join(trends[:2])} Trends suggest evolving inflammation. Increase monitoring."
        elif risk == 'WATCH':
            return f"Early warning. {trends[0] if trends else 'Mild abnormalities detected.'} Maintain close observation."
        else:
            return "Vitals stable. Continue routine monitoring."

# ========== MAIN SEWA SYSTEM ==========

class SEWASystem:
    """Main SEWA orchestrator - integrates all components."""
    
    def __init__(self, trend_engine, ml_model, patient_id: str = "UNKNOWN"):
        """
        Initialize SEWA system.
        
        Args:
            trend_engine: TrendRecognitionEngine instance
            ml_model: SEWARiskModel instance
            patient_id: Patient identifier
        """
        self.trend_engine = trend_engine
        self.ml_model = ml_model
        self.rule_engine = ClinicalRuleEngine()
        self.explainer = ExplanationGenerator()
        self.patient_id = patient_id
        self.alert_history = []
    
    def process_measurement(self, patient_state: PatientState) -> Optional[SEWAAlert]:
        """
        Process new measurement and generate alert if needed.
        
        This is the MAIN METHOD for real-time operation.
        """
        ts = patient_state.timestamp
        
        # Step 1: Add measurements to trend engine
        if patient_state.lactate is not None:
            self.trend_engine.add_measurement('lactate', ts, patient_state.lactate)
        if patient_state.map is not None:
            self.trend_engine.add_measurement('map', ts, patient_state.map)
        if patient_state.hr is not None:
            self.trend_engine.add_measurement('hr', ts, patient_state.hr)
        if patient_state.temp is not None:
            self.trend_engine.add_measurement('temp', ts, patient_state.temp)
        if patient_state.rr is not None:
            self.trend_engine.add_measurement('rr', ts, patient_state.rr)
        if patient_state.spo2 is not None:
            self.trend_engine.add_measurement('spo2', ts, patient_state.spo2)
        
        # Step 2: Extract trend features
        features = self.trend_engine.extract_all_features(ts)
        
        # Step 3: ML risk scoring
        ml_risk, ml_proba = self._compute_ml_risk(features)
        
        # Step 4: Apply rules
        final_risk, rules, reason = self.rule_engine.evaluate(
            patient_state, features, ml_risk
        )
        
        # Step 5: Extract clinical context
        trends = self._extract_trends(features)
        vitals = self._extract_concerning_vitals(patient_state)
        
        # Step 6: Determine action
        action = self.rule_engine.get_action(final_risk, rules)
        
        # Step 7: Create alert
        alert = SEWAAlert(
            patient_id=self.patient_id,
            timestamp=ts,
            ml_risk_level=ml_risk,
            final_risk_level=final_risk,
            risk_score=ml_proba[final_risk],
            rules_triggered=rules,
            override_applied=(final_risk != ml_risk),
            override_reason=reason,
            key_trends=trends,
            concerning_vitals=vitals,
            recommended_action=action,
            clinical_narrative=""
        )
        
        # Step 8: Generate explanation
        alert.clinical_narrative = self.explainer.generate(alert, patient_state)
        
        # Step 9: Store and return
        self.alert_history.append(alert)
        
        if final_risk >= RiskLevel.WATCH:
            return alert
        return None
    
    def _compute_ml_risk(self, features: Dict) -> Tuple[RiskLevel, Dict]:
        """Compute ML risk from features."""
        # Prepare features for ML
        X = pd.DataFrame([features])[self.ml_model.feature_names].fillna(0)
        
        # Predict
        pred_class = self.ml_model.predict(X)[0]
        pred_proba = self.ml_model.predict_proba(X)[0]
        
        # Convert to dict
        proba_dict = {RiskLevel(i): p for i, p in enumerate(pred_proba)}
        
        return RiskLevel(pred_class), proba_dict
    
    def _extract_trends(self, features: Dict) -> List[str]:
        """Extract human-readable trend descriptions."""
        trends = []
        
        # Lactate
        lac_slope = features.get('lactate_slope_short')
        if lac_slope and lac_slope > 0.3:
            trends.append(f"Lactate rising {lac_slope:.2f} mmol/L/hr")
        
        # MAP
        map_slope = features.get('map_slope_short')
        if map_slope and map_slope < -2.0:
            trends.append(f"MAP declining {abs(map_slope):.1f} mmHg/hr")
        
        # HR volatility
        hr_vol = features.get('hr_volatility_medium')
        if hr_vol and hr_vol > 10:
            trends.append(f"HR variability increased ({hr_vol:.1f} bpm)")
        
        return trends[:3]
    
    def _extract_concerning_vitals(self, state: PatientState) -> List[str]:
        """Identify abnormal vitals."""
        concerning = []
        
        if state.lactate and state.lactate > 2.0:
            concerning.append(f"Lactate {state.lactate:.1f} mmol/L")
        if state.map and state.map < 65:
            concerning.append(f"MAP {state.map:.0f} mmHg")
        if state.hr and state.hr > 100:
            concerning.append(f"HR {state.hr:.0f} bpm")
        if state.temp and state.temp > 38.0:
            concerning.append(f"Temp {state.temp:.1f}°C")
        if state.spo2 and state.spo2 < 92:
            concerning.append(f"SpO2 {state.spo2:.0f}%")
        
        return concerning
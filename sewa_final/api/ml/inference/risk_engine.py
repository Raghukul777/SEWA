"""
SEWA Core ML Engine — Clinical Inference & Risk Fusion
======================================================
Architected for high-performance hospital integration.
ML (LightGBM) + Rules (SIRS/qSOFA) + SHAP Explainability.
"""

import numpy as np
import pandas as pd
import warnings
import joblib
import structlog
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

from api.ml.inference.sirs_engine import SIRSEngine
from api.ml.inference.qsofa_engine import QSOFAEngine
from api.schemas import VitalSigns, SepsisAlert, RiskExplanation

logger = structlog.get_logger("sewa.core_engine")

class CoreMLEngine:
    """
    The "AI Brain" of the SEWA system.
    Strictly decoupled from UI/Frontend, focused on clinical accuracy and latency.
    """
    def __init__(self, artifacts_dir: Path = Path("api/ml/artifacts")):
        self.artifacts_dir = artifacts_dir
        self.model = None
        self.scaler = None
        self.explainer = None
        self.feature_names = None
        self.version = "2.1.0-core-engine"
        self.sirs = SIRSEngine()
        self.qsofa = QSOFAEngine()
        self.ready = self.load_artifacts()
        
    def load_artifacts(self) -> bool:
        """Atomic load of clinical artifacts with validation."""
        try:
            cal_path = self.artifacts_dir / "model_calibrated.joblib"
            raw_path = self.artifacts_dir / "model_raw.joblib"
            scaler_path = self.artifacts_dir / "scaler.joblib"
            shap_path = self.artifacts_dir / "shap_explainer.joblib"
            feat_path = self.artifacts_dir / "feature_names.joblib"
            feat_json = self.artifacts_dir / "feature_names.json"
            
            if feat_path.exists(): 
                self.feature_names = joblib.load(feat_path)
            elif feat_json.exists():
                import json
                with open(feat_json) as f:
                    self.feature_names = json.load(f)
            
            if cal_path.exists(): 
                self.model = joblib.load(cal_path)
            
            if scaler_path.exists(): 
                self.scaler = joblib.load(scaler_path)
            
            if raw_path.exists() and self.feature_names:
                import shap
                raw_model = joblib.load(raw_path)
                raw_feats = len(getattr(raw_model, 'feature_name_', [])) or getattr(raw_model, 'n_features_', 0)
                dict_feats = len(self.feature_names)
                
                if raw_feats and raw_feats != dict_feats:
                    logger.warning("shap_disabled", reason=f"Raw model has {raw_feats} features but scaler/dictionary expects {dict_feats}.")
                    self.explainer = None
                else:
                    self.explainer = shap.TreeExplainer(raw_model)
                    logger.info("explainer_loaded_from_raw_model", status="OK")
            elif shap_path.exists(): 
                self.explainer = joblib.load(shap_path)
                logger.info("explainer_loaded", status="OK")
            
            is_ready = self.model is not None and self.scaler is not None and self.feature_names is not None
            
            # Strict artifact consistency validation
            if is_ready:
                model_features = len(getattr(self.model, 'feature_name_', [])) or getattr(self.model, 'n_features_', 0)
                dict_features = len(self.feature_names)
                if model_features and model_features != dict_features:
                    logger.error("artifact_mismatch", 
                                 error=f"Model expects {model_features} features, but dictionary/scaler has {dict_features}. Disabling ML inference.",
                                 action="falling_back_to_clinical_rules")
                    is_ready = False
            
            if is_ready:
                logger.info("engine_ready", version=self.version)
            else:
                logger.warning("engine_degraded", missing="artifacts_or_mismatch")
            return is_ready
        except Exception as e:
            logger.error("artifact_load_error", error=str(e))
            return False

    def _build_feature_row(self, vitals: VitalSigns) -> Dict[str, Any]:
        """
        Signal normalization & Sensor noise filtering.
        Maps hardware-agnostic Pydantic inputs to internal ML tokens.
        """
        v = vitals.model_dump()
        
        # ── Hardware & Physiological Constraints ──
        # Defaulting to clinical normals if sensor data is null
        hr = v.get("heart_rate") or 80.0
        sbp = v.get("systolic_bp")
        dbp = v.get("diastolic_bp")
        rr = v.get("respiratory_rate") or 16.0
        temp = v.get("temperature_c") or 37.0
        spo2 = v.get("spo2_percent") or 98.0
        
        # ── Derived Clinical Vectors ──
        if v.get("map"):
            map_val = v.get("map")
            if not sbp: sbp = map_val + 20 # rough approx
            if not dbp: dbp = map_val - 10 # rough approx
        else:
            sbp = sbp or 120.0
            dbp = dbp or 80.0
            map_val = (sbp + 2 * dbp) / 3
            
        v["map"] = map_val
        v["si"] = hr / sbp if sbp > 0 else 0.7
        v["pp"] = sbp - dbp
        v["lac_hr"] = (v.get("lactate") or 1.0) * hr
        
        # ── Feature Mapping (Legacy Aliases) ──
        # Training dataset uses short names (hr, sbp...)
        mapping = {
            "heart_rate": "hr", "respiratory_rate": "rr", "temperature_c": "temp",
            "systolic_bp": "sbp", "diastolic_bp": "dbp", "spo2_percent": "spo2",
            "wbc_count": "wbc", "lactate": "lac", "creatinine": "creat",
            "bilirubin_total": "bili", "bun": "bun", "glucose": "gluc",
            "hemoglobin": "hgb", "platelets": "plt", "hours_since_admission": "icu_h"
        }
        
        internal_v = {}
        for long, short in mapping.items():
            val = v.get(long)
            internal_v[short] = float(val) if val is not None else 0.0
            internal_v[f"{short}_miss"] = 0 if val is not None else 1
            
        # Add scores and secondary derived
        internal_v["Age"] = v.get("age", 60.0)
        internal_v["Gender"] = v.get("gender", 1)
        
        return internal_v

    def rule_engine_overlay(self, ml_prob: float, sirs: int, qsofa: int, vitals: VitalSigns) -> Tuple[float, List[str]]:
        """
        Rule Engine Overlay: ML + Clinical Rule Fusion.
        Implements safety escalation logic (Conservative Bias).
        """
        overrides = []
        fused_prob = ml_prob
        
        # Safety Trigger: qSOFA >= 2 indicates high risk of mortality
        if qsofa >= 2 and fused_prob < 0.60:
            fused_prob = 0.65
            overrides.append("qSOFA Escalation Indicator")
            
        # Safety Trigger: SIRS >= 3 indicates acute inflammation
        if sirs >= 3 and fused_prob < 0.40:
            fused_prob = 0.45
            overrides.append("SIRS Acute Inflammation")

        # Hemodynamic Failsafe: Shock Index > 1.1 (High likelihood of septic shock)
        sbp = vitals.systolic_bp or 120.0
        hr = vitals.heart_rate or 80.0
        si = hr / sbp if sbp > 0 else 0
        if si > 1.1 and fused_prob < 0.75:
            fused_prob = 0.80
            overrides.append("Hemodynamic Shock Failsafe")

        return fused_prob, overrides

    def _get_risk_level(self, score: float) -> str:
        """Clinical threshold mapping."""
        if score >= 0.80: return "CRITICAL"
        if score >= 0.60: return "HIGH"
        if score >= 0.40: return "MODERATE"
        return "LOW"

    def predict(self, vitals: VitalSigns) -> SepsisAlert:
        """
        Top-level inference pipeline.
        POST /predict (VitalSigns) -> _build_feature_row -> [Engines] -> rule_engine_overlay -> SepsisAlert
        """
        start_ts = datetime.now(timezone.utc)
        
        # 1. Feature Engineering & Normalization
        feat_dict = self._build_feature_row(vitals)
        
        # 2. Execution of Deterministic Rule Engines
        sirs_res = self.sirs.evaluate(vitals.model_dump(), vitals.model_dump())
        qsofa_res = self.qsofa.evaluate(vitals.model_dump())
        
        # 3. Execution of Probabilistic ML Engine
        ml_prob = 0.0
        confidence = 0.95
        if self.ready:
            # Build vector in artifact order
            try:
                X_df = pd.DataFrame([[float(feat_dict.get(f, 0.0)) for f in self.feature_names]], columns=self.feature_names)
                X_scaled = self.scaler.transform(X_df)
                X_scaled_df = pd.DataFrame(X_scaled, columns=self.feature_names)
                ml_prob = float(self.model.predict_proba(X_scaled_df)[0, 1])
            except Exception as e:
                logger.error("ml_inference_failed", error=str(e))
                confidence = 0.4 # Significant drop in confidence
        else:
            confidence = 0.4
            
        # 4. Rule Engine Overlay & Risk Level Mapping
        fused_score, overrides = self.rule_engine_overlay(ml_prob, sirs_res["sirs_score"], qsofa_res["qsofa_score"], vitals)
        risk_level = self._get_risk_level(fused_score)
        
        # 5. Explainability Layer (Optimized SHAP)
        explanations = RiskExplanation(clinical_factors=overrides)
        if self.explainer and self.ready:
            try:
                # Use pre-scaled X
                X_df_v = pd.DataFrame([[float(feat_dict.get(f, 0.0)) for f in self.feature_names]], columns=self.feature_names)
                X_v = self.scaler.transform(X_df_v)
                X_v_df = pd.DataFrame(X_v, columns=self.feature_names)
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)
                    sv = self.explainer.shap_values(X_v)
                
                if isinstance(sv, list): sv = sv[1] if len(sv) > 1 else sv[0]
                vals = sv.flatten()
                
                # Extract top 5 drivers
                pairs = sorted(zip(self.feature_names, vals.tolist()), key=lambda x: abs(x[1]), reverse=True)
                explanations.top_features = [{"feature": f, "impact": round(i, 4)} for f, i in pairs[:5]]
                explanations.shap_values = {f: round(i, 4) for f, i in pairs[:10]}
            except Exception as e:
                logger.warning("shap_error", error=str(e))

        return SepsisAlert(
            patient_id=vitals.patient_id,
            risk_score=round(fused_score, 4),
            risk_level=risk_level,
            ml_probability=round(ml_prob, 4),
            sirs_score=sirs_res["sirs_score"],
            qsofa_score=qsofa_res["qsofa_score"],
            rule_overrides=overrides,
            explanations=explanations,
            confidence=confidence,
            model_version=self.version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            system_health="OK" if self.ready else "DEGRADED"
        )

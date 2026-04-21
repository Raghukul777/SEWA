"""
SEWA Vital Signs + ML Scoring Routes

POST /vitals/{patient_id}
  - Stores the vital reading in DB
  - Runs the SEWA ML pipeline (TrendRecognitionEngine → SEWASystem)
  - Generates alerts and audit logs if risk is elevated
  - Returns reading + risk assessment + optional alert

GET /vitals/{patient_id}
  - Returns last N readings for a patient
"""

import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db, Patient, VitalReading, Alert, AuditLog
from .schemas import VitalReadingRequest, VitalReadingOut, RiskAssessmentOut, VitalResponseOut, VitalSigns
from .auth import get_current_user, User
from fastapi import Request

router = APIRouter(prefix="/vitals", tags=["vitals"])


# ── ML Integration Helpers ───────────────────────────────────────────

def _run_rule_based_risk(readings_history: List[VitalReading]) -> Dict[str, Any]:
    """
    Pure rule-based sepsis risk assessment (no ML model required).
    Mirrors the logic in SepsisEngine.js so the API matches frontend expectations.
    Returns a dict compatible with RiskAssessmentOut.
    """
    if not readings_history:
        return {
            "riskLevel": "LOW", "criteria": [], "actions": [],
            "summary": "No vitals available", "riskScore": 0,
        }

    criteria: List[str] = []
    actions: List[str] = []
    risk_score = 0

    recent = readings_history[-5:]
    latest = readings_history[-1]

    # Rule 1: Sustained hypotension (MAP < 65 mmHg for 2+ readings)
    low_map = [r for r in recent if r.map and r.map < 65]
    if len(low_map) >= 2:
        criteria.append(f"Sustained hypotension: MAP < 65 mmHg in {len(low_map)} of last {len(recent)} readings")
        actions.append("Consider fluid resuscitation (30 mL/kg crystalloid)")
        actions.append("Assess for vasopressor requirement")
        risk_score += 3 if len(low_map) >= 3 else 2

    # Rule 2: Rising lactate trend
    lactate_vals = [r.lactate for r in recent if r.lactate is not None]
    if len(lactate_vals) >= 3:
        rising = sum(1 for i in range(1, len(lactate_vals)) if lactate_vals[i] > lactate_vals[i-1])
        if rising >= 2:
            criteria.append(f"Rising lactate trend: {lactate_vals[0]:.1f} → {lactate_vals[-1]:.1f} mmol/L")
            actions.append("Repeat lactate measurement in 2-4 hours")
            if lactate_vals[-1] > 2:
                actions.append("Initiate sepsis workup if not already done")
                risk_score += 2
            risk_score += 3 if lactate_vals[-1] > 4 else 1

    # Rule 3: Sustained tachypnea (RR > 22)
    high_rr = [r for r in recent if r.respiratory_rate and r.respiratory_rate > 22]
    if len(high_rr) >= 2:
        criteria.append(f"Sustained tachypnea: RR > 22/min in {len(high_rr)} readings")
        actions.append("Monitor for respiratory distress")
        risk_score += 2 if len(high_rr) >= 3 else 1

    # Rule 4: Fever/Hypothermia
    if latest.temperature:
        if latest.temperature > 38.3:
            criteria.append(f"Fever: {latest.temperature:.1f}°C")
            actions.append("Obtain blood cultures if not done")
            risk_score += 1
        elif latest.temperature < 36.0:
            criteria.append(f"Hypothermia: {latest.temperature:.1f}°C")
            actions.append("Consider septic shock workup")
            risk_score += 2

    # Rule 5: Sustained tachycardia (HR > 100)
    high_hr = [r for r in recent if r.heart_rate and r.heart_rate > 100]
    if len(high_hr) >= 2:
        criteria.append(f"Sustained tachycardia: HR > 100 bpm in {len(high_hr)} readings")
        risk_score += 1

    # Rule 6: Oxygen desaturation (SpO2 < 94%)
    low_spo2 = [r for r in recent if r.spo2 and r.spo2 < 94]
    if len(low_spo2) >= 2:
        criteria.append(f"Oxygen desaturation: SpO₂ < 94% in {len(low_spo2)} readings")
        actions.append("Increase supplemental oxygen")
        risk_score += 2

    # Rule 7: WBC abnormality
    if latest.wbc and (latest.wbc > 12 or latest.wbc < 4):
        label = "Leukocytosis" if latest.wbc > 12 else "Leukopenia"
        criteria.append(f"{label}: WBC {latest.wbc:.1f} ×10³/μL")
        risk_score += 1

    # Rule 8: Elevated creatinine
    if latest.creatinine and latest.creatinine > 1.2:
        criteria.append(f"Elevated creatinine: {latest.creatinine:.2f} mg/dL")
        actions.append("Monitor urine output")
        risk_score += 2 if latest.creatinine > 2 else 1

    # Determine risk level
    risk_level = "LOW"
    if risk_score >= 6:
        risk_level = "HIGH"
    elif risk_score >= 3:
        risk_level = "MODERATE"

    # General recommendations
    if risk_level == "HIGH" and "Notify attending physician immediately" not in actions:
        actions.insert(0, "Notify attending physician immediately")
        actions.append("Consider ICU upgrade if in general ward")
    if risk_level == "MODERATE" and "Increase monitoring frequency to q15min" not in actions:
        actions.insert(0, "Increase monitoring frequency to q15min")

    # Clinical summary
    parts = []
    if latest.map: parts.append(f"MAP {latest.map} mmHg")
    if latest.heart_rate: parts.append(f"HR {latest.heart_rate} bpm")
    if latest.respiratory_rate: parts.append(f"RR {latest.respiratory_rate}/min")
    if latest.spo2: parts.append(f"SpO₂ {latest.spo2}%")
    if latest.lactate: parts.append(f"Lactate {latest.lactate:.1f} mmol/L")
    vitals_str = ", ".join(parts)

    if risk_level == "HIGH":
        summary = f"Critical: {len(criteria)} warning criteria triggered. {vitals_str}"
    elif risk_level == "MODERATE":
        summary = f"Concerning trends detected. {vitals_str}"
    else:
        summary = f"Stable parameters. {vitals_str}"

    return {
        "riskLevel": risk_level,
        "criteria": criteria,
        "actions": actions[:5],
        "summary": summary,
        "riskScore": risk_score,
        "ml_risk_level": "",
        "final_risk_level": risk_level,
        "clinical_narrative": summary,
        "rules_triggered": criteria,
    }


def _try_ml_risk(app_state: Any, patient_id: str, reading: VitalReading) -> Optional[Dict[str, Any]]:
    """
    Attempt to use the SEWA ML system for risk scoring.
    Returns None if ML model is not available or errors out.
    """
    try:
        from ..sewa.trend_engine import TrendRecognitionEngine
        from ..sewa.core_system import SEWASystem, PatientState, RiskLevel

        # Get or create per-patient SEWASystem from app state cache
        if not hasattr(app_state, "sewa_systems"):
            app_state.sewa_systems = {}

        if patient_id not in app_state.sewa_systems:
            if not hasattr(app_state, "ml_model") or app_state.ml_model is None:
                return None
            vital_names = ["lactate", "map", "hr", "temp", "rr", "spo2"]
            trend_engine = TrendRecognitionEngine(vital_names)
            app_state.sewa_systems[patient_id] = SEWASystem(
                trend_engine=trend_engine,
                ml_model=app_state.ml_model,
                patient_id=patient_id,
            )

        sewa = app_state.sewa_systems[patient_id]

        ts = reading.timestamp or datetime.utcnow()
        state = PatientState(
            timestamp=ts,
            lactate=reading.lactate,
            map=reading.map,
            hr=reading.heart_rate,
            temp=reading.temperature,
            rr=reading.respiratory_rate,
            spo2=reading.spo2,
        )

        alert = sewa.process_measurement(state)

        if alert:
            risk_map = {"NO_RISK": "LOW", "WATCH": "LOW", "MODERATE": "MODERATE",
                        "HIGH": "HIGH", "CRITICAL": "HIGH"}
            return {
                "riskLevel": risk_map.get(alert.final_risk_level.name, "LOW"),
                "criteria": alert.key_trends + alert.concerning_vitals,
                "actions": [],
                "summary": alert.clinical_narrative,
                "riskScore": alert.risk_score,
                "ml_risk_level": alert.ml_risk_level.name,
                "final_risk_level": alert.final_risk_level.name,
                "clinical_narrative": alert.clinical_narrative,
                "rules_triggered": alert.rules_triggered,
            }
        else:
            return {
                "riskLevel": "LOW", "criteria": [], "actions": [],
                "summary": "Vitals stable. No sepsis criteria met.",
                "riskScore": 0, "ml_risk_level": "NO_RISK",
                "final_risk_level": "NO_RISK", "clinical_narrative": "",
                "rules_triggered": [],
            }
    except Exception as e:
        print(f"[SEWA ML] Skipping ML, using rule-based fallback: {e}")
        return None


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/{patient_id}", response_model=dict)
def post_vital_reading(
    patient_id: str,
    body: VitalReadingRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Retrieve patient
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Parse timestamp from frontend if provided
    ts = datetime.utcnow()
    if body.timestamp:
        try:
            ts = datetime.fromisoformat(body.timestamp.replace("Z", "+00:00"))
            ts = ts.replace(tzinfo=None)
        except Exception:
            pass

    # Store reading
    reading = VitalReading(
        patient_id=patient_id,
        timestamp=ts,
        heart_rate=body.heart_rate,
        spo2=body.spo2,
        temperature=body.temperature,
        sbp=body.sbp,
        map=body.map,
        dbp=body.dbp,
        respiratory_rate=body.respiratory_rate,
        lactate=body.lactate,
        wbc=body.wbc,
        creatinine=body.creatinine,
    )
    db.add(reading)
    db.flush()  # get ID without committing

    # Retrieve recent readings for trend analysis
    recent_readings = (
        db.query(VitalReading)
        .filter(VitalReading.patient_id == patient_id)
        .order_by(VitalReading.timestamp.desc())
        .limit(20)
        .all()
    )
    recent_readings = list(reversed(recent_readings))  # chronological order

    # Evaluate ML Risk
    engine = request.app.state.ml_engine
    if engine and hasattr(engine, "predict"):
        vs = VitalSigns(
            patient_id=patient_id,
            heart_rate=body.heart_rate,
            spo2_percent=body.spo2,
            temperature_c=body.temperature,
            systolic_bp=body.sbp,
            diastolic_bp=body.dbp,
            map=body.map,
            respiratory_rate=body.respiratory_rate,
            lactate=body.lactate,
            wbc_count=body.wbc,
            creatinine=body.creatinine,
            age=patient.age,
            gender=1 if patient.gender.lower() == 'male' else 0,
            hours_since_admission=(datetime.utcnow() - patient.admission_date.replace(tzinfo=None)).total_seconds() / 3600 if patient.admission_date else 0
        )
        
        try:
            # Predict using new ML Engine
            alert_obj = engine.predict(vs)
            
            # Formulate the response Dictionary similar to _run_rule_based_risk
            clinical_factors = alert_obj.rule_overrides.copy()
            if alert_obj.explanations and alert_obj.explanations.top_features:
                clinical_factors.extend([f"{f['feature']} (impact: {f['impact']})" for f in alert_obj.explanations.top_features])
            
            risk = {
                "riskLevel": alert_obj.risk_level,
                "criteria": clinical_factors,
                "actions": ["Notify attending physician!"] if alert_obj.risk_level in ("HIGH", "CRITICAL") else ["Monitor vitals closely"],
                "summary": " | ".join(alert_obj.rule_overrides) if alert_obj.rule_overrides else "ML Risk Assessment completed.",
                "riskScore": alert_obj.risk_score,
                "ml_risk_level": "N/A", 
                "final_risk_level": alert_obj.risk_level,
                "clinical_narrative": "",
                "rules_triggered": alert_obj.rule_overrides,
            }
        except Exception as e:
            print(f"[SEWA ML] Skipping ML, predict failed: {e}")
            risk = _run_rule_based_risk(recent_readings)
    else:
        risk = _run_rule_based_risk(recent_readings)

    # Update patient status
    status_map = {"LOW": "Stable", "MODERATE": "Warning", "HIGH": "Critical", "CRITICAL": "Critical"}
    new_status = status_map.get(risk["riskLevel"], "Stable")
    if patient.status != new_status:
        patient.status = new_status
        _log_audit_db(db, "patient_status_changed",
                      "warning" if new_status != "Stable" else "info",
                      patient_id, patient.name, "system",
                      f"Risk level changed: {patient.status} → {new_status}")

    # Generate alert if MODERATE or HIGH or CRITICAL
    alert_dict = None

    # If patient is now stable, auto-resolve any open pending alerts
    if risk["riskLevel"] == "LOW":
        db.query(Alert).filter(
            Alert.patient_id == patient_id,
            Alert.feedback == "pending",
            Alert.is_active == True,
        ).update({"is_active": False, "feedback": "auto_resolved"}, synchronize_session=False)

    elif risk["riskLevel"] in ("MODERATE", "HIGH", "CRITICAL"):
        from datetime import timedelta
        now = datetime.utcnow()

        # Rule 1: Block if doctor hasn't reviewed the current active alert yet
        active_pending = db.query(Alert).filter(
            Alert.patient_id == patient_id,
            Alert.feedback == "pending",
            Alert.is_active == True,
        ).first()

        # Rule 2: Global 5-minute cooldown per patient
        five_mins_ago = now - timedelta(minutes=5)
        any_recent = db.query(Alert).filter(
            Alert.patient_id == patient_id,
            Alert.timestamp >= five_mins_ago
        ).first()

        # Rule 3: Same-risk-level block for 30 minutes (no exact duplicates)
        thirty_mins_ago = now - timedelta(minutes=30)
        recent_alert = db.query(Alert).filter(
            Alert.patient_id == patient_id,
            Alert.risk_level == risk["riskLevel"],
            Alert.timestamp >= thirty_mins_ago
        ).first()

        suppressed = bool(active_pending) or bool(any_recent) or bool(recent_alert)

        if not suppressed:
            # ── Final existence gate: one last check before writing to DB ──
            already_in_db = db.query(Alert).filter(
                Alert.patient_id == patient_id,
                Alert.risk_level == risk["riskLevel"],
                Alert.feedback == "pending",
                Alert.is_active == True,
            ).first()

            if already_in_db:
                alert_dict = {
                    "id":                  already_in_db.id,
                    "patient_id":          patient_id,
                    "timestamp":           already_in_db.timestamp.isoformat(),
                    "risk_level":          already_in_db.risk_level,
                    "clinical_summary":    already_in_db.clinical_summary,
                    "param_values":        already_in_db.param_values,
                    "triggered_criteria":  already_in_db.triggered_criteria,
                    "recommended_actions": already_in_db.recommended_actions,
                    "feedback":            already_in_db.feedback,
                    "is_active":           already_in_db.is_active,
                }
            else:
                alert_id = str(uuid.uuid4())
                vital_snapshot = {
                    "heart_rate": body.heart_rate, "spo2": body.spo2,
                    "temperature": body.temperature, "map": body.map,
                    "respiratory_rate": body.respiratory_rate, "lactate": body.lactate,
                    "wbc": body.wbc, "creatinine": body.creatinine,
                }
                alert = Alert(
                    id                  = alert_id,
                    patient_id          = patient_id,
                    timestamp           = ts,
                    risk_level          = risk["riskLevel"],
                    clinical_summary    = risk["summary"],
                    param_values        = vital_snapshot,
                    triggered_criteria  = risk["criteria"],
                    recommended_actions = risk["actions"],
                    feedback            = "pending",
                    is_active           = True,
                )
                db.add(alert)
                # NOTE: trg_alert_audit trigger will automatically write to audit_logs

                alert_dict = {
                    "id":                  alert_id,
                    "patient_id":          patient_id,
                    "timestamp":           ts.isoformat(),
                    "risk_level":          risk["riskLevel"],
                    "clinical_summary":    risk["summary"],
                    "param_values":        vital_snapshot,
                    "triggered_criteria":  risk["criteria"],
                    "recommended_actions": risk["actions"],
                    "feedback":            "pending",
                    "is_active":           True,
                }

    db.commit()
    db.refresh(reading)

    return {
        "reading": {
            "id": reading.id,
            "patient_id": reading.patient_id,
            "timestamp": reading.timestamp.isoformat(),
            "heart_rate": reading.heart_rate,
            "spo2": reading.spo2,
            "temperature": reading.temperature,
            "sbp": reading.sbp,
            "map": reading.map,
            "dbp": reading.dbp,
            "respiratory_rate": reading.respiratory_rate,
            "lactate": reading.lactate,
            "wbc": reading.wbc,
            "creatinine": reading.creatinine,
        },
        "risk_assessment": risk,
        "alert": alert_dict,
    }


@router.get("/{patient_id}", response_model=List[dict])
def get_vital_readings(
    patient_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    readings = (
        db.query(VitalReading)
        .filter(VitalReading.patient_id == patient_id)
        .order_by(VitalReading.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "timestamp": r.timestamp.isoformat(),
            "heart_rate": r.heart_rate,
            "spo2": r.spo2,
            "temperature": r.temperature,
            "sbp": r.sbp,
            "map": r.map,
            "dbp": r.dbp,
            "respiratory_rate": r.respiratory_rate,
            "lactate": r.lactate,
            "wbc": r.wbc,
            "creatinine": r.creatinine,
        }
        for r in reversed(readings)
    ]


def _log_audit_db(db, event_type, severity, patient_id, patient_name, user_email, description):
    log = AuditLog(
        timestamp=datetime.utcnow(),
        event_type=event_type,
        severity=severity,
        patient_id=patient_id,
        patient_name=patient_name,
        user_email=user_email,
        event_description=description,
    )
    db.add(log)

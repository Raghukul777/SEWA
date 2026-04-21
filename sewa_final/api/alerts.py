"""
SEWA Alert Management Routes
PostgreSQL upgrade: param_values, triggered_criteria, recommended_actions
are now JSONB columns — no json.loads() needed, returned as Python objects.
The trg_alert_feedback_audit trigger automatically writes audit_log entries.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db, Alert, Patient
from .schemas import FeedbackRequest
from .auth import get_current_user, User

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _serialize_alert(a: Alert) -> dict:
    """JSONB fields are already Python dicts/lists — no json.loads needed."""
    return {
        "id":                  a.id,
        "patient_id":          a.patient_id,
        "timestamp":           a.timestamp.isoformat(),
        "risk_level":          a.risk_level,
        "clinical_summary":    a.clinical_summary,
        # JSONB → Python object directly
        "param_values":        a.param_values        if isinstance(a.param_values, dict)  else {},
        "triggered_criteria":  a.triggered_criteria  if isinstance(a.triggered_criteria,  list) else [],
        "recommended_actions": a.recommended_actions if isinstance(a.recommended_actions, list) else [],
        "feedback":            a.feedback,
        "is_active":           a.is_active,
    }


@router.get("", response_model=List[dict])
def get_alerts(
    patient_id:  Optional[str]  = Query(None),
    active_only: bool           = Query(False),
    risk_level:  Optional[str]  = Query(None, description="Filter: LOW | MODERATE | HIGH | CRITICAL"),
    db:          Session        = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    """
    Return alerts — filtered by patient, status, and/or risk level.
    Only alerts for the current doctor's patients are returned.
    """
    # Join with patients to scope by doctor_id
    query = (
        db.query(Alert)
        .join(Patient, Alert.patient_id == Patient.patient_id)
        .filter(Patient.doctor_id == current_user.id)
    )
    if patient_id:
        query = query.filter(Alert.patient_id == patient_id)
    if active_only:
        query = query.filter(Alert.is_active == True)
    if risk_level:
        query = query.filter(Alert.risk_level == risk_level.upper())

    alerts = query.order_by(Alert.timestamp.desc()).limit(200).all()
    return [_serialize_alert(a) for a in alerts]


@router.put("/{alert_id}/feedback")
def submit_feedback(
    alert_id: str,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit clinician feedback on an alert.
    The PostgreSQL trigger `trg_alert_feedback_audit` automatically
    writes to audit_logs — no manual audit call needed.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")

    alert.feedback = body.feedback
    if body.feedback in ("approved", "false_positive"):
        alert.is_active = False

    db.commit()
    return {"message": "Feedback recorded", "feedback": body.feedback}


@router.get("/stats", response_model=dict)
def alert_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregate alert statistics for the current doctor's patients.
    Uses index-backed COUNT queries via partial indexes.
    """
    row = db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE a.is_active = TRUE AND a.feedback = 'pending')    AS pending,
                COUNT(*) FILTER (WHERE a.risk_level = 'HIGH'   AND a.is_active = TRUE)   AS high,
                COUNT(*) FILTER (WHERE a.risk_level = 'MODERATE' AND a.is_active = TRUE) AS moderate,
                COUNT(*) FILTER (WHERE a.feedback = 'approved')                          AS approved,
                COUNT(*) FILTER (WHERE a.feedback = 'false_positive')                    AS false_positive
            FROM alerts a
            JOIN patients p ON p.patient_id = a.patient_id
            WHERE p.doctor_id = :doctor_id
        """),
        {"doctor_id": current_user.id}
    ).fetchone()

    return {
        "pending":        row.pending        if row else 0,
        "high":           row.high           if row else 0,
        "moderate":       row.moderate       if row else 0,
        "approved":       row.approved       if row else 0,
        "false_positive": row.false_positive if row else 0,
    }

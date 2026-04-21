"""
SEWA Admin Routes — Hospital-wide management endpoints.
Only accessible to users with role = 'Administrator'.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from .database import get_db, User, Patient, Alert, AuditLog
from .auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Guard helper ─────────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: raises 403 if the caller is not an Administrator."""
    if current_user.role != "Administrator":
        raise HTTPException(
            status_code=403,
            detail="Access denied: Administrator role required."
        )
    return current_user


# ── Hospital-wide stats ───────────────────────────────────────────────

@router.get("/stats", response_model=dict)
def hospital_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Hospital-wide KPI snapshot:
      - Total / active / critical patients
      - Total doctors
      - Pending / high-risk alerts
    """
    patient_row = db.execute(text("""
        SELECT
            COUNT(*)                                         AS total_patients,
            COUNT(*) FILTER (WHERE is_active = TRUE)         AS active_patients,
            COUNT(*) FILTER (WHERE status = 'Critical'
                             AND is_active = TRUE)           AS critical_patients,
            COUNT(*) FILTER (WHERE status = 'Warning'
                             AND is_active = TRUE)           AS warning_patients
        FROM patients
    """)).fetchone()

    alert_row = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE feedback = 'pending'
                             AND is_active = TRUE)           AS pending_alerts,
            COUNT(*) FILTER (WHERE risk_level = 'HIGH'
                             AND is_active = TRUE)           AS high_alerts,
            COUNT(*) FILTER (WHERE risk_level = 'MODERATE'
                             AND is_active = TRUE)           AS moderate_alerts,
            COUNT(*) FILTER (WHERE feedback = 'false_positive') AS false_positives
        FROM alerts
    """)).fetchone()

    doctor_count = db.query(User).filter(
        User.role == "Doctor", User.is_active == True
    ).count()

    return {
        "total_patients":    patient_row.total_patients    if patient_row else 0,
        "active_patients":   patient_row.active_patients   if patient_row else 0,
        "critical_patients": patient_row.critical_patients if patient_row else 0,
        "warning_patients":  patient_row.warning_patients  if patient_row else 0,
        "total_doctors":     doctor_count,
        "pending_alerts":    alert_row.pending_alerts      if alert_row else 0,
        "high_alerts":       alert_row.high_alerts         if alert_row else 0,
        "moderate_alerts":   alert_row.moderate_alerts     if alert_row else 0,
        "false_positives":   alert_row.false_positives     if alert_row else 0,
    }


# ── Doctor directory ──────────────────────────────────────────────────

@router.get("/doctors", response_model=List[dict])
def list_doctors(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Return all registered doctors with per-doctor patient stats."""
    doctors = db.query(User).filter(User.role == "Doctor").all()

    result = []
    for doc in doctors:
        stats = db.execute(
            text("SELECT * FROM fn_doctor_patient_count(:did)"),
            {"did": doc.id}
        ).fetchone()

        result.append({
            "id":            doc.id,
            "name":          doc.name,
            "email":         doc.email,
            "hospital_name": doc.hospital_name or "",
            "department":    doc.department or "",
            "phone":         doc.phone or "",
            "is_active":     doc.is_active,
            "created_at":    doc.created_at.isoformat() if doc.created_at else None,
            "last_login_at": doc.last_login_at.isoformat() if doc.last_login_at else None,
            "active_patients":  stats.active_count   if stats else 0,
            "critical_patients": stats.critical_count if stats else 0,
            "total_patients":   stats.total_count    if stats else 0,
        })

    return result


# ── All patients (hospital-wide) ──────────────────────────────────────

@router.get("/patients", response_model=List[dict])
def all_patients(
    status:  Optional[str] = Query(None, description="Stable | Warning | Critical"),
    search:  Optional[str] = Query(None),
    db:      Session = Depends(get_db),
    admin:   User = Depends(require_admin),
):
    """All active patients across every doctor — admin view."""
    stmt_parts = [
        """
        SELECT p.patient_id, p.name, p.age, p.gender, p.bed_number,
               p.status, p.trajectory, p.admission_date, p.is_active,
               p.doctor_id, u.name AS doctor_name, u.department AS doctor_department
        FROM patients p
        LEFT JOIN users u ON p.doctor_id = u.id
        WHERE p.is_active = TRUE
        """
    ]
    params: dict = {}

    if status and status != "all":
        stmt_parts.append("AND p.status = :status")
        params["status"] = status

    if search:
        stmt_parts.append("AND p.name ILIKE :search")
        params["search"] = f"%{search}%"

    stmt_parts.append("ORDER BY p.status DESC, p.admission_date ASC")
    rows = db.execute(text(" ".join(stmt_parts)), params).fetchall()

    return [
        {
            "patient_id":        r.patient_id,
            "name":              r.name,
            "age":               r.age,
            "gender":            r.gender,
            "bed_number":        r.bed_number,
            "status":            r.status,
            "trajectory":        r.trajectory,
            "admission_date":    r.admission_date.isoformat() if r.admission_date else None,
            "is_active":         r.is_active,
            "doctor_id":         r.doctor_id,
            "doctor_name":       r.doctor_name or "Unassigned",
            "doctor_department": r.doctor_department or "",
        }
        for r in rows
    ]


# ── Deactivate / reactivate a doctor ─────────────────────────────────

@router.put("/doctors/{doctor_id}/toggle-active")
def toggle_doctor_active(
    doctor_id: str,
    db:    Session = Depends(get_db),
    admin: User    = Depends(require_admin),
):
    """Toggle a doctor's is_active flag (deactivate / reactivate)."""
    doctor = db.query(User).filter(
        User.id == doctor_id, User.role == "Doctor"
    ).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    doctor.is_active = not doctor.is_active
    db.commit()

    action = "activated" if doctor.is_active else "deactivated"
    return {"message": f"Doctor {doctor.name} {action} successfully.", "is_active": doctor.is_active}


# ── Refresh analytics materialized view ──────────────────────────────

@router.post("/refresh-stats")
def refresh_stats(
    db:    Session = Depends(get_db),
    admin: User    = Depends(require_admin),
):
    """Refresh the mv_patient_stats materialized view."""
    from sqlalchemy import text as sql
    from .database import engine
    with engine.connect() as conn:
        conn.execute(sql("SELECT refresh_patient_stats()"))
        conn.commit()
    return {"message": "Analytics refreshed successfully."}

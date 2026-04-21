"""
SEWA Patient Management Routes
Admit, list, discharge patients; manage notes and treatment bundles.

PostgreSQL upgrades:
  - GET /patients uses the `active_patients_summary` VIEW (LATERAL JOIN + pre-joined vitals)
  - JSONB stored natively — no json.loads/json.dumps overhead for treatment_bundle / medical_history
  - Alert suppression uses the `fn_alert_suppressed()` DB function
  - Search uses the trigram index (ILIKE on name via pg_trgm)
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db, Patient, VitalReading, ClinicalNote, AuditLog
from .schemas import (
    AdmitPatientRequest, PatientOut, UpdateTreatmentRequest, AddNoteRequest
)
from .auth import get_current_user, User

router = APIRouter(prefix="/patients", tags=["patients"])


# ── Serialisation helpers ─────────────────────────────────────────────

def _serialize_patient(patient: Patient, db: Session) -> dict:
    """Convert ORM Patient → dict for API response. Reads ClinicalNotes from DB."""
    # Latest vital reading
    latest_vital = (
        db.query(VitalReading)
        .filter(VitalReading.patient_id == patient.patient_id)
        .order_by(VitalReading.timestamp.desc())
        .first()
    )
    latest_vitals = None
    if latest_vital:
        latest_vitals = {
            "patient_id": latest_vital.patient_id,
            "timestamp": latest_vital.timestamp.isoformat(),
            "heart_rate": latest_vital.heart_rate,
            "spo2": latest_vital.spo2,
            "temperature": latest_vital.temperature,
            "sbp": latest_vital.sbp,
            "map": latest_vital.map,
            "dbp": latest_vital.dbp,
            "respiratory_rate": latest_vital.respiratory_rate,
            "lactate": latest_vital.lactate,
            "wbc": latest_vital.wbc,
            "creatinine": latest_vital.creatinine,
        }

    # Clinical notes (sorted newest first)
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.patient_id == patient.patient_id)
        .order_by(ClinicalNote.timestamp.desc())
        .all()
    )
    notes_list = [
        {"id": n.id, "text": n.text, "author": n.author,
         "timestamp": n.timestamp.isoformat()}
        for n in notes
    ]

    # JSONB fields come back as Python dicts/lists directly — no json.loads needed
    medical_history  = patient.medical_history  if isinstance(patient.medical_history,  list) else []
    treatment_bundle = patient.treatment_bundle if isinstance(patient.treatment_bundle, dict) else {}

    return {
        "patient_id":               patient.patient_id,
        "doctor_id":                patient.doctor_id,
        "name":                     patient.name,
        "age":                      patient.age,
        "gender":                   patient.gender,
        "blood_group":              patient.blood_group or "",
        "bed_number":               patient.bed_number,
        "admission_reason":         patient.admission_reason or "",
        "admission_date":           patient.admission_date.isoformat() if patient.admission_date else None,
        "trajectory":               patient.trajectory,
        "medical_history":          medical_history,
        "treatment_bundle":         treatment_bundle,
        "status":                   patient.status,
        "is_active":                patient.is_active,
        "clinical_notes":           notes_list,
        "latest_vitals":            latest_vitals,
        "phone":                    patient.phone or "",
        "emergency_contact_name":   patient.emergency_contact_name or "",
        "emergency_contact_phone":  patient.emergency_contact_phone or "",
        "address":                  patient.address or "",
        "updated_at":               patient.updated_at.isoformat() if patient.updated_at else None,
    }


def _serialize_from_view_row(row) -> dict:
    """
    Convert a row from active_patients_summary VIEW to API dict.
    Much faster than _serialize_patient — no extra DB round-trips.
    """
    latest_vitals = None
    if row.vitals_timestamp:
        latest_vitals = {
            "timestamp":        row.vitals_timestamp.isoformat(),
            "heart_rate":       row.heart_rate,
            "spo2":             row.spo2,
            "temperature":      row.temperature,
            "sbp":              row.sbp,
            "dbp":              row.dbp,
            "map":              row.map,
            "respiratory_rate": row.respiratory_rate,
            "lactate":          row.lactate,
            "wbc":              row.wbc,
            "creatinine":       row.creatinine,
        }

    return {
        "patient_id":               row.patient_id,
        "doctor_id":                row.doctor_id,
        "name":                     row.name,
        "age":                      row.age,
        "gender":                   row.gender,
        "blood_group":              row.blood_group or "",
        "bed_number":               row.bed_number,
        "admission_reason":         row.admission_reason or "",
        "admission_date":           row.admission_date.isoformat() if row.admission_date else None,
        "trajectory":               row.trajectory,
        "medical_history":          row.medical_history or [],
        "treatment_bundle":         row.treatment_bundle or {},
        "status":                   row.status,
        "is_active":                row.is_active,
        "clinical_notes":           [],          # fetched separately when detail needed
        "latest_vitals":            latest_vitals,
        "phone":                    row.phone or "",
        "emergency_contact_name":   row.emergency_contact_name or "",
        "emergency_contact_phone":  row.emergency_contact_phone or "",
        "address":                  row.address or "",
        "active_alert_count":       row.active_alert_count,
        "note_count":               row.note_count,
        "updated_at":               row.updated_at.isoformat() if row.updated_at else None,
    }


def _log_audit(db: Session, event_type: str, severity: str,
               patient_id: str, patient_name: str,
               user_email: str, description: str):
    """
    Manual audit entry for events that are NOT covered by DB triggers.
    Note: status changes, discharges, and alert events are now auto-audited
    by PostgreSQL triggers in pg_setup.sql — no need to log those here.
    """
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


# ── Routes ───────────────────────────────────────────────────────────

@router.get("", response_model=List[dict])
def list_patients(
    search:  Optional[str] = Query(None, description="Fuzzy name search (uses pg_trgm index)"),
    status:  Optional[str] = Query(None, description="Filter by status: Stable | Warning | Critical"),
    db:      Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return active patients belonging to the current doctor.
    Uses the `active_patients_summary` VIEW — single query, pre-joined latest vitals.
    Optionally filter by patient name (trigram) or status.
    """
    stmt_parts = [
        "SELECT * FROM active_patients_summary",
        "WHERE doctor_id = :doctor_id",
    ]
    params: dict = {"doctor_id": current_user.id}

    if status and status != "all":
        stmt_parts.append("AND status = :status")
        params["status"] = status

    if search:
        # pg_trgm ILIKE search uses the GIN trigram index on patients.name
        stmt_parts.append("AND name ILIKE :search")
        params["search"] = f"%{search}%"

    stmt_parts.append("ORDER BY status DESC, admission_date ASC")
    stmt = text(" ".join(stmt_parts))

    rows = db.execute(stmt, params).fetchall()
    return [_serialize_from_view_row(r) for r in rows]


@router.post("", response_model=dict, status_code=201)
def admit_patient(
    body: AdmitPatientRequest,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admit a new patient under the current doctor.
    Automatically links patient to synthetic data for vitals streaming.
    JSONB fields (medical_history, treatment_bundle) stored natively.
    The discharge audit trigger fires automatically on subsequent discharge.
    """
    from .patient_data_sync import find_available_synthetic_patient, link_patient_to_synthetic_data

    patient_id = f"P-{uuid.uuid4().hex[:5].upper()}"

    patient = Patient(
        patient_id       = patient_id,
        doctor_id        = current_user.id,
        name             = body.name,
        age              = body.age,
        gender           = body.gender,
        blood_group      = body.blood_group or "",
        bed_number       = body.bed_number,
        admission_reason = body.admission_reason,
        admission_date   = datetime.utcnow(),
        trajectory       = body.trajectory,
        # JSONB — pass Python objects directly, SQLAlchemy handles serialisation
        medical_history  = body.medical_history or [],
        treatment_bundle = body.treatment_bundle or {
            "lactate_measure": False,
            "blood_cultures":  False,
            "antibiotics":     False,
            "fluids":          False,
            "vasopressors":    False,
        },
        status           = "Stable",
        is_active        = True,
        phone                   = body.phone or "",
        emergency_contact_name  = body.emergency_contact_name or "",
        emergency_contact_phone = body.emergency_contact_phone or "",
        address                 = body.address or "",
    )
    db.add(patient)
    db.flush()  # Get the patient ID

    # Link to synthetic data for vitals streaming
    synthetic_id = find_available_synthetic_patient()
    if synthetic_id is not None:
        link_patient_to_synthetic_data(db, patient_id, synthetic_id)
        admission_msg = f"Patient {body.name} admitted to bed {body.bed_number}. Linked to synthetic data ID {synthetic_id}"
    else:
        admission_msg = f"Patient {body.name} admitted to bed {body.bed_number}. WARNING: No synthetic data available for vitals"

    # Manual audit for admission (trigger doesn't cover INSERT, only UPDATE)
    _log_audit(db, "patient_admitted", "info", patient_id, body.name,
               current_user.email, admission_msg)

    db.commit()
    db.refresh(patient)
    return _serialize_patient(patient, db)


@router.get("/{patient_id}", response_model=dict)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full patient detail including all clinical notes."""
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.doctor_id  == current_user.id,   # scoped to this doctor
    ).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    return _serialize_patient(patient, db)


@router.put("/{patient_id}/discharge")
def discharge_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Discharge a patient (sets is_active=False).
    PostgreSQL trigger `trg_patient_discharge_audit` automatically:
      - Stamps discharge_date
      - Writes an audit_log entry
    No manual audit call needed here.
    """
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.doctor_id  == current_user.id,
    ).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    patient.is_active = False   # ← trigger fires here
    db.commit()
    return {"message": "Patient discharged successfully"}


@router.put("/{patient_id}/treatment")
def update_treatment(
    patient_id: str,
    body: UpdateTreatmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a single key in the JSONB treatment_bundle using PostgreSQL's
    jsonb_set() operator — efficient in-place JSONB mutation.
    """
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.doctor_id  == current_user.id,
    ).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Use jsonb_set for atomic JSONB field update
    db.execute(
        text("""
            UPDATE patients
            SET    treatment_bundle = jsonb_set(
                       treatment_bundle,
                       :key_path,
                       :value::jsonb,
                       true           -- create key if missing
                   ),
                   updated_at = NOW() AT TIME ZONE 'UTC'
            WHERE  patient_id = :patient_id
        """),
        {
            "key_path":   f'{{{body.key}}}',
            "value":      json.dumps(body.value),
            "patient_id": patient_id,
        }
    )

    _log_audit(db, "treatment_updated", "info", patient_id, patient.name,
               current_user.email,
               f"Treatment '{body.key}' → {body.value}")
    db.commit()

    # Return updated bundle
    db.refresh(patient)
    return {"treatment_bundle": patient.treatment_bundle}


@router.post("/{patient_id}/notes", status_code=201)
def add_note(
    patient_id: str,
    body: AddNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.doctor_id  == current_user.id,
    ).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    note = ClinicalNote(
        id         = str(uuid.uuid4()),
        patient_id = patient_id,
        text       = body.text,
        author     = body.author or current_user.name,
        timestamp  = datetime.utcnow(),
    )
    db.add(note)

    _log_audit(db, "clinical_note_added", "info", patient_id, patient.name,
               current_user.email,
               f"Clinical note added by {body.author or current_user.name}")
    db.commit()
    db.refresh(note)
    return {
        "id":        note.id,
        "text":      note.text,
        "author":    note.author,
        "timestamp": note.timestamp.isoformat(),
    }


@router.get("/{patient_id}/risk-history", response_model=List[dict])
def patient_risk_history(
    patient_id: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Daily risk event counts for a patient using the DB function
    `fn_patient_risk_history` — avoids full table scan.
    """
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.doctor_id  == current_user.id,
    ).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    rows = db.execute(
        text("SELECT * FROM fn_patient_risk_history(:pid, :days)"),
        {"pid": patient_id, "days": days}
    ).fetchall()

    return [
        {
            "day":         str(r.day),
            "critical_ct": r.critical_ct,
            "warning_ct":  r.warning_ct,
            "info_ct":     r.info_ct,
        }
        for r in rows
    ]


@router.get("/stats/me", response_model=dict)
def my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Quick doctor KPI stats using the DB function `fn_doctor_patient_count`.
    Returns active, critical, and total patient counts without a full scan.
    """
    row = db.execute(
        text("SELECT * FROM fn_doctor_patient_count(:did)"),
        {"did": current_user.id}
    ).fetchone()

    return {
        "active_patients":  row.active_count  if row else 0,
        "critical_patients": row.critical_count if row else 0,
        "total_patients":   row.total_count   if row else 0,
    }

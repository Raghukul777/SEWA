"""
SEWA Data Source Management Routes
===================================
Admin endpoints to view and manage synthetic patient data mappings.

GET  /admin/data/stats - View overall synthetic data statistics
GET  /admin/data/patient/{patient_id} - View synthetic mapping for a patient
POST /admin/data/patient/{patient_id}/relink - Relink patient to different synthetic data
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db
from .auth import get_current_user, User
from .data_loader import get_data_statistics, get_patient_data_range
from .patient_data_sync import get_patient_with_synthetic_mapping

router = APIRouter(prefix="/admin/data", tags=["data-management"])


@router.get("/stats")
def get_data_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get overall statistics about the synthetic patient data and system.
    Only accessible to administrators.
    """
    if current_user.role not in ["Administrator", "Doctor"]:
        raise HTTPException(status_code=403, detail="Only admins can access data statistics")

    try:
        # Synthetic data statistics
        synthetic_stats = get_data_statistics()

        # Database statistics
        db_result = db.execute(text("""
            SELECT 
                COUNT(*) as total_patients,
                COUNT(CASE WHEN synthetic_data_id IS NOT NULL THEN 1 END) as patients_with_synthetic_data,
                COUNT(CASE WHEN is_active THEN 1 END) as active_patients,
                COUNT(CASE WHEN synthetic_data_id IS NOT NULL AND is_active THEN 1 END) as active_with_data
            FROM patients
        """)).first()

        return {
            "synthetic_data": synthetic_stats,
            "database": {
                "total_patients": db_result[0],
                "patients_linked_to_synthetic_data": db_result[1],
                "active_patients": db_result[2],
                "active_patients_with_data_stream": db_result[3],
            },
            "integration_status": "healthy" if synthetic_stats.get('total_readings', 0) > 0 else "no_data",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/patient/{patient_id}")
def get_patient_data_mapping(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the synthetic data mapping and statistics for a specific patient.
    """
    try:
        patient_info = get_patient_with_synthetic_mapping(db, patient_id)

        if not patient_info:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        # Check authorization (doctor can only see their own patients)
        if current_user.role == "Doctor":
            patient_owner = db.execute(text(
                "SELECT doctor_id FROM patients WHERE patient_id = :pid"
            ), {"pid": patient_id}).first()

            if not patient_owner or patient_owner[0] != current_user.id:
                raise HTTPException(status_code=403, detail="You don't have permission to view this patient")

        return patient_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patient mapping: {str(e)}")


@router.post("/patient/{patient_id}/relink")
def relink_patient_to_data(
    patient_id: str,
    synthetic_data_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Relink a patient to different synthetic data (e.g., if current data is exhausted).
    Only administrators can do this.
    """
    if current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Only administrators can relink patient data")

    try:
        # Verify patient exists
        patient_result = db.execute(text(
            "SELECT patient_id, name FROM patients WHERE patient_id = :pid"
        ), {"pid": patient_id}).first()

        if not patient_result:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        # Verify synthetic data exists
        data_range = get_patient_data_range(synthetic_data_id)
        if not data_range:
            raise HTTPException(status_code=404, detail=f"Synthetic data {synthetic_data_id} not found")

        # Update the link
        db.execute(text("""
            UPDATE patients 
            SET synthetic_data_id = :synthetic_id,
                data_sync_started_at = CURRENT_TIMESTAMP
            WHERE patient_id = :patient_id
        """), {
            'synthetic_id': synthetic_data_id,
            'patient_id': patient_id
        })
        db.commit()

        return {
            "status": "success",
            "message": f"Patient {patient_id} relinked to synthetic data {synthetic_data_id}",
            "patient_id": patient_id,
            "synthetic_data_id": synthetic_data_id,
            "data_range": data_range,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to relink patient: {str(e)}")


@router.get("/unlinked-patients")
def get_unlinked_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of active patients not yet linked to synthetic data.
    This helps identify patients that need data sources assigned.
    """
    if current_user.role not in ["Administrator", "Doctor"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        results = db.execute(text("""
            SELECT 
                patient_id, name, admission_date, bed_number, doctor_id
            FROM patients
            WHERE is_active = true 
            AND synthetic_data_id IS NULL
            ORDER BY admission_date DESC
        """)).fetchall()

        return {
            "count": len(results),
            "patients": [
                {
                    "patient_id": r[0],
                    "name": r[1],
                    "admission_date": r[2].isoformat() if r[2] else None,
                    "bed_number": r[3],
                    "doctor_id": r[4],
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unlinked patients: {str(e)}")



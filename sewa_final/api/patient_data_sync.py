"""
SEWA — Patient Data Synchronization Manager
============================================
Manages the mapping between registered patients in the DB and
synthetic patient data from the CSV file.

When a doctor registers a patient:
  1. The system searches for matching synthetic data
  2. Links the registered patient_id with the synthetic patient_id
  3. Subsequent vital readings are pulled from the synthetic data

This decouples patient registration (doctor-managed) from data generation
(system-managed via CSV), allowing realistic ICU monitoring.

Database schema addition:
  - Add 'synthetic_data_id' column to patients table
  - Track when data sync started/ended
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from .data_loader import get_patient_data_range, get_all_patient_ids

logger = logging.getLogger(__name__)


def find_available_synthetic_patient() -> Optional[int]:
    """
    Find an unused synthetic patient in the CSV data.
    This is called during patient registration to assign data source.

    Returns:
        A synthetic patient_id that can be used, or None if all are in use.
    """
    available_ids = get_all_patient_ids()

    if not available_ids:
        logger.warning("No synthetic patient data available")
        return None

    # For now, just return the first available
    # In production, could implement more sophisticated allocation
    return available_ids[0]


def link_patient_to_synthetic_data(db: Session,
                                    patient_id: str,
                                    synthetic_patient_id: int) -> bool:
    """
    Link a registered patient to synthetic data.

    Args:
        db: Database session
        patient_id: The registered patient's ID (e.g., "P-1001")
        synthetic_patient_id: The synthetic data patient ID (e.g., 683)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Update the patient record with synthetic data link
        update_stmt = text("""
            UPDATE patients 
            SET synthetic_data_id = :synthetic_id,
                data_sync_started_at = :now
            WHERE patient_id = :patient_id
        """)

        db.execute(update_stmt, {
            'synthetic_id': synthetic_patient_id,
            'patient_id': patient_id,
            'now': datetime.utcnow()
        })
        db.commit()

        logger.info(f"Linked patient {patient_id} to synthetic data {synthetic_patient_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to link patient {patient_id} to synthetic data: {e}")
        db.rollback()
        return False


def get_synthetic_data_for_patient(db: Session, patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the synthetic data source linked to a registered patient.

    Args:
        db: Database session
        patient_id: The registered patient's ID

    Returns:
        Dict with synthetic_data_id and metadata, or None
    """
    try:
        result = db.execute(text("""
            SELECT synthetic_data_id, data_sync_started_at
            FROM patients
            WHERE patient_id = :patient_id
        """), {'patient_id': patient_id}).first()

        if not result or result[0] is None:
            return None

        synthetic_id = result[0]
        sync_started = result[1]

        # Get data range for this synthetic patient
        data_range = get_patient_data_range(synthetic_id)

        return {
            'synthetic_data_id': synthetic_id,
            'sync_started_at': sync_started.isoformat() if sync_started else None,
            'data_range': data_range,
        }

    except Exception as e:
        logger.error(f"Failed to get synthetic data for patient {patient_id}: {e}")
        return None


def unlink_patient_from_synthetic_data(db: Session, patient_id: str) -> bool:
    """
    Unlink a patient from synthetic data (e.g., on discharge).

    Args:
        db: Database session
        patient_id: The registered patient's ID

    Returns:
        True if successful, False otherwise
    """
    try:
        update_stmt = text("""
            UPDATE patients 
            SET synthetic_data_id = NULL,
                data_sync_ended_at = :now
            WHERE patient_id = :patient_id
        """)

        db.execute(update_stmt, {
            'patient_id': patient_id,
            'now': datetime.utcnow()
        })
        db.commit()

        logger.info(f"Unlinked patient {patient_id} from synthetic data")
        return True

    except Exception as e:
        logger.error(f"Failed to unlink patient {patient_id}: {e}")
        db.rollback()
        return False


def get_patient_with_synthetic_mapping(db: Session, patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Get complete patient info including synthetic data mapping.

    Args:
        db: Database session
        patient_id: The registered patient's ID

    Returns:
        Dict with patient info + synthetic mapping, or None
    """
    try:
        result = db.execute(text("""
            SELECT 
                p.patient_id,
                p.name,
                p.synthetic_data_id,
                p.data_sync_started_at,
                p.data_sync_ended_at,
                p.status,
                p.is_active
            FROM patients p
            WHERE p.patient_id = :patient_id
        """), {'patient_id': patient_id}).first()

        if not result:
            return None

        synthetic_id = result[2]
        data_range = get_patient_data_range(synthetic_id) if synthetic_id else None

        return {
            'patient_id': result[0],
            'name': result[1],
            'synthetic_data_id': synthetic_id,
            'data_sync_started_at': result[3].isoformat() if result[3] else None,
            'data_sync_ended_at': result[4].isoformat() if result[4] else None,
            'data_range': data_range,
            'status': result[5],
            'is_active': result[6],
        }

    except Exception as e:
        logger.error(f"Failed to get patient with mapping {patient_id}: {e}")
        return None


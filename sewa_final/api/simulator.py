"""
SEWA — Vital Sign Data Source Adapter
======================================
This is the SINGLE file you replace when connecting a real ICU device.

Current mode: SYNTHETIC DATA FROM CSV
  - Reads vitals from synthetic_patients.csv (ICU monitoring simulation)
  - Maps registered patients to synthetic data sources
  - Streams realistic vital signs based on pre-recorded data
  - Runs entirely in the backend — browser tab can be closed, monitoring continues

Future mode: REAL ICU DEVICE
  - Replace `get_next_reading()` with your device SDK / HL7 reader / serial port call
  - Everything else (WebSocket pipeline, DB persistence, alert engine) stays identical

Architecture:
  ICU Data Source (CSV or Real Device)
        │
        ▼
  get_next_reading(patient)        ← SWAP THIS for real device
        │
        ▼
  WebSocket /ws/vitals/{patient_id}
        │
        ▼
  React Dashboard (display only)
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .data_loader import get_next_vitals_from_data, reset_patient_index
from .database import SessionLocal

logger = logging.getLogger(__name__)


# ── Public API ────────────────────────────────────────────────────────────────

def get_next_reading(patient_id: str, trajectory: str = None, initial_vitals: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get the next vital reading for a patient from the synthetic data source.

    ┌─────────────────────────────────────────────────────────────────────┐
    │  DEVICE INTEGRATION POINT                                           │
    │  This function now reads from synthetic_patients.csv data.          │
    │  To integrate real device:                                          │
    │                                                                     │
    │  1. Replace get_next_vitals_from_data() with your device SDK       │
    │  2. Map device fields to the vitals dict below                     │
    │  3. Everything else (WebSocket, DB, alerts) stays identical        │
    │                                                                     │
    │  Example for HL7 integration:                                       │
    │  async def get_next_reading(patient_id, ...):                      │
    │      raw = await hl7_client.fetch_latest(patient_id)               │
    │      return {                                                       │
    │          "heart_rate":       raw.HR,                               │
    │          "respiratory_rate": raw.RR,                               │
    │          "map":              raw.MAP,                              │
    │          "temperature":      raw.TEMP,                             │
    │          "spo2":             raw.SPO2,                             │
    │          "lactate":          raw.LACTATE,                          │
    │          "wbc":              raw.WBC,                              │
    │          "creatinine":       raw.CREAT,                            │
    │          "timestamp":        raw.TIMESTAMP,                        │
    │      }                                                              │
    └─────────────────────────────────────────────────────────────────────┘

    Args:
        patient_id:      Registered patient ID (e.g., "P-1001")
        trajectory:      Ignored when using data source (for backward compatibility)
        initial_vitals:  Ignored when using data source (for backward compatibility)

    Returns:
        Dict with all vital signs + patient_id + timestamp from synthetic data.
        Falls back to empty readings if synthetic data not available.
    """
    from .database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # 1. Look up the synthetic patient ID linked to this registered patient
        result = db.execute(text("""
            SELECT synthetic_data_id FROM patients WHERE patient_id = :patient_id
        """), {'patient_id': patient_id}).first()

        if not result or result[0] is None:
            logger.warning(f"Patient {patient_id} not linked to synthetic data. No vitals available.")
            return {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "heart_rate": None,
                "respiratory_rate": None,
                "map": None,
                "temperature": None,
                "spo2": None,
                "lactate": None,
                "wbc": None,
                "creatinine": None,
            }

        synthetic_id = result[0]

        # 2. Get next vitals from the synthetic data source
        vitals = get_next_vitals_from_data(synthetic_id)

        # 3. If the hardcoded ID (e.g. 1) isn't in the CSV, pick a random valid one
        if vitals is None:
            import random
            from .data_loader import get_all_patient_ids
            all_ids = get_all_patient_ids()
            if all_ids:
                new_sync_id = random.choice(all_ids)
                logger.warning(f"Synthetic ID {synthetic_id} not in CSV. Remapping patient {patient_id} to valid ID {new_sync_id}")
                db.execute(text("UPDATE patients SET synthetic_data_id = :sid WHERE patient_id = :pid"), 
                           {'sid': new_sync_id, 'pid': patient_id})
                db.commit()
                synthetic_id = new_sync_id
                vitals = get_next_vitals_from_data(synthetic_id)
                
        if vitals is None:
            logger.warning(f"No more synthetic data for patient {patient_id} (synthetic ID: {synthetic_id})")
            return {
                "patient_id": patient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "heart_rate": None,
                "respiratory_rate": None,
                "map": None,
                "temperature": None,
                "spo2": None,
                "lactate": None,
                "wbc": None,
                "creatinine": None,
            }

        # 3. Ensure patient_id in response is the registered ID (not synthetic)
        vitals['patient_id'] = patient_id

        return vitals

    except Exception as e:
        logger.error(f"Error getting next reading for patient {patient_id}: {e}")
        return {
            "patient_id": patient_id,
            "timestamp": datetime.utcnow().isoformat(),
            "heart_rate": None,
            "respiratory_rate": None,
            "map": None,
            "temperature": None,
            "spo2": None,
            "lactate": None,
            "wbc": None,
            "creatinine": None,
        }
    finally:
        db.close()

def reset_patient(patient_id: str) -> None:
    """
    Reset the data streaming for a patient.
    Called on re-admission or when restarting monitoring.
    """
    from .database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT synthetic_data_id FROM patients WHERE patient_id = :patient_id
        """), {'patient_id': patient_id}).first()

        if result and result[0] is not None:
            synthetic_id = result[0]
            reset_patient_index(synthetic_id)
            logger.info(f"Reset data stream for patient {patient_id} (synthetic ID: {synthetic_id})")
    except Exception as e:
        logger.error(f"Error resetting patient {patient_id}: {e}")
    finally:
        db.close()

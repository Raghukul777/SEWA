"""
SEWA — Synthetic Patient Data Loader
=====================================
Loads the synthetic_patients.csv file and provides an interface to stream
vitals data for patients. This acts as a simulated ICU monitoring system
that will be replaced by real device data in the future.

Features:
  - In-memory lazy loading of CSV data
  - Patient-specific data streaming
  - Caching for performance
  - Easy to swap for real device integration

When real ICU data arrives:
  - Keep this same interface (get_patient_vitals_from_data_source)
  - Replace the CSV reading with device SDK calls
  - Everything else remains identical
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Global cache for the CSV data
_synthetic_data: Optional[pd.DataFrame] = None
_data_file_path: Optional[Path] = None

# Track reading positions per patient for streaming
_patient_reading_index: Dict[str, int] = {}


def initialize_data_loader(csv_path: Optional[Path] = None) -> bool:
    """
    Load the synthetic patients CSV into memory.
    Call this once during application startup.

    Args:
        csv_path: Path to synthetic_patients.csv. If None, searches for it.

    Returns:
        True if loaded successfully, False otherwise.
    """
    global _synthetic_data, _data_file_path

    try:
        # Auto-locate the file if not provided
        if csv_path is None:
            base_dir = Path(__file__).parent.parent
            csv_path = base_dir / "data" / "synthetic_patients.csv"

        if not csv_path.exists():
            logger.error(f"Synthetic data file not found: {csv_path}")
            return False

        logger.info(f"Loading synthetic patients data from {csv_path}")
        _synthetic_data = pd.read_csv(csv_path)
        _data_file_path = csv_path

        # Ensure required columns exist
        required_cols = {'patient_id', 'timestamp', 'lactate', 'map', 'hr', 'temp', 'rr', 'spo2', 'risk_label'}
        if not required_cols.issubset(_synthetic_data.columns):
            logger.error(f"Missing required columns. Expected: {required_cols}, Got: {set(_synthetic_data.columns)}")
            return False

        # Rename columns to match vitals format (for easier integration)
        _synthetic_data = _synthetic_data.rename(columns={
            'hr': 'heart_rate',
            'temp': 'temperature',
            'rr': 'respiratory_rate',
            'risk_label': 'risk_category'
        })

        # Convert timestamp to datetime
        _synthetic_data['timestamp'] = pd.to_datetime(_synthetic_data['timestamp'])

        logger.info(f"✅ Loaded {len(_synthetic_data)} vital readings for {_synthetic_data['patient_id'].nunique()} unique patients")
        return True

    except Exception as e:
        logger.error(f"Failed to load synthetic data: {e}")
        return False


def get_patient_data_range(patient_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the available data range for a specific patient.

    Args:
        patient_id: The synthetic patient ID

    Returns:
        Dict with 'min_time', 'max_time', 'reading_count' or None if patient not found
    """
    if _synthetic_data is None:
        return None

    patient_data = _synthetic_data[_synthetic_data['patient_id'] == patient_id]
    if patient_data.empty:
        return None

    return {
        'patient_id': patient_id,
        'min_time': patient_data['timestamp'].min().isoformat(),
        'max_time': patient_data['timestamp'].max().isoformat(),
        'reading_count': len(patient_data),
    }


def get_next_vitals_from_data(patient_id: int, start_from_index: int = 0) -> Optional[Dict[str, Any]]:
    """
    Get the next vital reading from the synthetic data for a patient.

    Use this instead of simulator.get_next_reading() to pull from actual data.

    Args:
        patient_id: The synthetic patient ID
        start_from_index: Start from a specific index in the patient's data

    Returns:
        Dict with vitals + metadata, or None if no more data available
    """
    if _synthetic_data is None:
        logger.warning("Data loader not initialized. Call initialize_data_loader() first.")
        return None

    patient_data = _synthetic_data[_synthetic_data['patient_id'] == patient_id].reset_index(drop=True)

    if patient_data.empty:
        logger.warning(f"No synthetic data found for patient {patient_id}")
        return None

    # Get current index for this patient
    current_idx = _patient_reading_index.get(patient_id, start_from_index)

    if current_idx >= len(patient_data):
        # Loop back to start or return None depending on use case
        logger.debug(f"Reached end of data for patient {patient_id}. Looping back to start.")
        current_idx = 0

    row = patient_data.iloc[current_idx]

    # Increment index for next call
    _patient_reading_index[patient_id] = current_idx + 1

    # Build vitals dict, handling NaN values
    vitals = {
        'patient_id': int(row['patient_id']),
        'timestamp': row['timestamp'].isoformat(),
        'heart_rate': float(row['heart_rate']) if pd.notna(row['heart_rate']) else None,
        'respiratory_rate': float(row['respiratory_rate']) if pd.notna(row['respiratory_rate']) else None,
        'map': float(row['map']) if pd.notna(row['map']) else None,
        'temperature': float(row['temperature']) if pd.notna(row['temperature']) else None,
        'spo2': float(row['spo2']) if pd.notna(row['spo2']) else None,
        'lactate': float(row['lactate']) if pd.notna(row['lactate']) else None,
        'wbc': None,  # Not in current CSV
        'creatinine': None,  # Not in current CSV
        'risk_category': int(row['risk_category']) if pd.notna(row['risk_category']) else 0,
    }

    return vitals


def reset_patient_index(patient_id: int) -> None:
    """Reset the reading index for a patient (e.g., on re-admission)."""
    _patient_reading_index[patient_id] = 0
    logger.debug(f"Reset reading index for patient {patient_id}")


def get_all_patient_ids() -> List[int]:
    """Get a list of all unique patient IDs in the synthetic data."""
    if _synthetic_data is None:
        return []
    return sorted(_synthetic_data['patient_id'].unique().tolist())


def get_data_statistics() -> Dict[str, Any]:
    """Get overall statistics about the loaded synthetic data."""
    if _synthetic_data is None:
        return {}

    return {
        'total_readings': len(_synthetic_data),
        'unique_patients': _synthetic_data['patient_id'].nunique(),
        'date_range_start': _synthetic_data['timestamp'].min().isoformat(),
        'date_range_end': _synthetic_data['timestamp'].max().isoformat(),
        'available_patient_ids': get_all_patient_ids(),
    }


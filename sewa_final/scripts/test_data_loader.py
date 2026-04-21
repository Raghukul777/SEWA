"""
Integration test script to verify the synthetic data loader works correctly.
Run this before deploying to ensure everything is configured properly.
"""

import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.data_loader import (
    initialize_data_loader,
    get_all_patient_ids,
    get_data_statistics,
    get_next_vitals_from_data,
    get_patient_data_range
)


def test_data_loader():
    """Run comprehensive tests on the data loader."""

    print("=" * 70)
    print("SEWA SYNTHETIC DATA LOADER - INTEGRATION TEST")
    print("=" * 70)

    # Test 1: Initialize loader
    print("\n[Test 1] Initializing data loader...")
    if not initialize_data_loader():
        print("❌ FAILED: Could not initialize data loader")
        return False
    print("✅ PASSED: Data loader initialized")

    # Test 2: Get statistics
    print("\n[Test 2] Retrieving data statistics...")
    stats = get_data_statistics()
    if not stats or stats.get('total_readings', 0) == 0:
        print("❌ FAILED: No data loaded")
        return False
    print(f"✅ PASSED: Loaded {stats['total_readings']} readings")
    print(f"   - Unique patients: {stats['unique_patients']}")
    print(f"   - Date range: {stats['date_range_start']} to {stats['date_range_end']}")

    # Test 3: Get patient IDs
    print("\n[Test 3] Retrieving available patient IDs...")
    patient_ids = get_all_patient_ids()
    if not patient_ids:
        print("❌ FAILED: No patient IDs found")
        return False
    print(f"✅ PASSED: Found {len(patient_ids)} unique patients")
    print(f"   - Sample IDs: {patient_ids[:5]}")

    # Test 4: Get patient data range
    print("\n[Test 4] Checking data range for first patient...")
    first_patient = patient_ids[0]
    data_range = get_patient_data_range(first_patient)
    if not data_range:
        print(f"❌ FAILED: Could not get data range for patient {first_patient}")
        return False
    print(f"✅ PASSED: Patient {first_patient}")
    print(f"   - Readings: {data_range['reading_count']}")
    print(f"   - Range: {data_range['min_time']} to {data_range['max_time']}")

    # Test 5: Stream vitals
    print("\n[Test 5] Streaming vitals for patient...")
    vitals1 = get_next_vitals_from_data(first_patient, 0)
    vitals2 = get_next_vitals_from_data(first_patient, 1)

    if not vitals1 or not vitals2:
        print("❌ FAILED: Could not get vitals")
        return False

    print(f"✅ PASSED: Got 2 consecutive readings")
    print(f"   - Reading 1: HR={vitals1.get('heart_rate')}, MAP={vitals1.get('map')}, Lactate={vitals1.get('lactate')}")
    print(f"   - Reading 2: HR={vitals2.get('heart_rate')}, MAP={vitals2.get('map')}, Lactate={vitals2.get('lactate')}")

    # Test 6: Verify data integrity
    print("\n[Test 6] Verifying data integrity...")
    has_nulls = False
    for key in ['patient_id', 'timestamp']:
        if vitals1.get(key) is None:
            print(f"❌ FAILED: Missing required field {key}")
            return False

    print("✅ PASSED: All required fields present")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print("\nSystem is ready for deployment!")
    return True


if __name__ == "__main__":
    try:
        success = test_data_loader()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


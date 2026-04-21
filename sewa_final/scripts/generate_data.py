#!/usr/bin/env python3
"""
SEWA Data Generation Script

Generates synthetic patient cohort for ML training.
Usage: python generate_data.py --patients-per-class 200 --output data/synthetic_patients.csv
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sewa.data_generator import SyntheticCohortGenerator


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic patient data for SEWA training'
    )
    parser.add_argument(
        '--patients-per-class',
        type=int,
        default=200,
        help='Number of patients per risk class (default: 200)'
    )
    parser.add_argument(
        '--duration-hours',
        type=int,
        default=12,
        help='Simulation duration per patient in hours (default: 12)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/synthetic_patients.csv',
        help='Output CSV path (default: data/synthetic_patients.csv)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate data
    print(f"\n{'='*70}")
    print("SEWA SYNTHETIC DATA GENERATION")
    print(f"{'='*70}\n")
    print(f"Configuration:")
    print(f"  Patients per class: {args.patients_per_class}")
    print(f"  Duration per patient: {args.duration_hours} hours")
    print(f"  Total patients: {args.patients_per_class * 5}")
    print(f"  Output: {args.output}")
    print()
    
    generator = SyntheticCohortGenerator(
        n_patients_per_class=args.patients_per_class,
        duration_hours=args.duration_hours
    )
    
    cohort = generator.generate_cohort(save_path=args.output)
    
    print(f"\n{'='*70}")
    print("✓ DATA GENERATION COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
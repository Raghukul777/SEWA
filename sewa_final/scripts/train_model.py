#!/usr/bin/env python3
"""
SEWA Model Training Script

Trains ML risk scoring model on synthetic patient data.
Usage: python train_model.py --data data/synthetic_patients.csv --model-type logistic
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sewa.ml_pipeline import train_sewa_model


def main():
    parser = argparse.ArgumentParser(
        description='Train SEWA risk scoring model'
    )
    parser.add_argument(
        '--data',
        type=str,
        required=True,
        help='Path to synthetic patient CSV'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        choices=['logistic', 'gradient_boosting'],
        default='logistic',
        help='Model type (default: logistic)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='models/sewa_risk_model.pkl',
        help='Output model path (default: models/sewa_risk_model.pkl)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set fraction (default: 0.2)'
    )
    
    args = parser.parse_args()
    
    # Validate data file exists
    if not Path(args.data).exists():
        print(f"Error: Data file not found: {args.data}")
        print("Run generate_data.py first to create synthetic dataset")
        sys.exit(1)
    
    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print(f"\nLoading data from {args.data}...")
    cohort_df = pd.read_csv(args.data, parse_dates=['timestamp'])
    
    # Train model
    model = train_sewa_model(
        cohort_df=cohort_df,
        model_type=args.model_type,
        save_model_path=args.output
    )
    
    print(f"\n{'='*70}")
    print("✓ MODEL TRAINING COMPLETE")
    print(f"{'='*70}")
    print(f"\nModel saved to: {args.output}")
    print(f"Model type: {args.model_type}")
    print("\nNext steps:")
    print("  1. Run test_system.py to validate end-to-end pipeline")
    print("  2. Review model performance metrics above")
    print("  3. Configure LLM API in .env file")
    print()


if __name__ == "__main__":
    main()
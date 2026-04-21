"""
SEWA - Sepsis Early Warning Agent
Artifact 2: Synthetic Patient Data Generator

Generates realistic patient trajectories with multi-class risk labels
for training the SEWA risk scoring model.

Simulation Strategy:
- Sine-wave based progression for smooth, realistic trends
- 5 risk classes: NO_RISK, WATCH, MODERATE, HIGH, CRITICAL
- Includes noise, missing data, and sensor artifacts
- Outputs timestamped vital signs with ground truth labels

Author: SEWA Development Team
Version: 1.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import IntEnum
import warnings
warnings.filterwarnings('ignore')


class RiskLevel(IntEnum):
    """Multi-class risk stratification labels."""
    NO_RISK = 0    # Normal physiology, routine monitoring
    WATCH = 1      # Early warning signs, monitor closely
    MODERATE = 2   # Concerning trends, prepare intervention
    HIGH = 3       # Imminent sepsis risk, immediate action
    CRITICAL = 4   # Septic shock likely, emergency protocol


class PatientTrajectory:
    """
    Generates a single patient's vital sign trajectory over time.
    
    Each patient follows one of 5 progression patterns corresponding
    to the 5 risk levels.
    """
    
    def __init__(self, patient_id: int, risk_class: RiskLevel, 
                 duration_hours: int = 12, measurement_interval_min: int = 15):
        """
        Initialize patient trajectory generator.
        
        Args:
            patient_id: Unique patient identifier
            risk_class: Target risk level (determines progression pattern)
            duration_hours: Total simulation duration
            measurement_interval_min: Time between measurements
        """
        self.patient_id = patient_id
        self.risk_class = risk_class
        self.duration_hours = duration_hours
        self.interval_min = measurement_interval_min
        
        # Calculate number of measurements
        self.n_measurements = int(duration_hours * 60 / measurement_interval_min)
        
        # Time array (in hours)
        self.time_hours = np.linspace(0, duration_hours, self.n_measurements)
        
        # Baseline vitals (normal ranges)
        self.baseline = {
            'lactate': 1.2,   # mmol/L
            'map': 75,        # mmHg
            'hr': 80,         # bpm
            'temp': 37.0,     # °C
            'rr': 16,         # breaths/min
            'spo2': 98        # %
        }
        
    def _generate_progression_pattern(self, vital: str) -> np.ndarray:
        """
        Generate vital sign progression based on risk class.
        
        Uses sine-wave modulation for smooth, realistic trends.
        
        Args:
            vital: Name of vital sign
            
        Returns:
            Array of vital sign values over time
        """
        t = self.time_hours
        baseline = self.baseline[vital]
        
        # Risk-specific progression patterns
        if self.risk_class == RiskLevel.NO_RISK:
            # Stable with minor random fluctuation
            trend = np.zeros_like(t)
            noise_scale = 0.05
            
        elif self.risk_class == RiskLevel.WATCH:
            # Mild trend in one direction (early warning)
            if vital == 'lactate':
                trend = 0.3 * np.sin(np.pi * t / self.duration_hours)
            elif vital == 'map':
                trend = -3 * np.sin(np.pi * t / self.duration_hours)
            elif vital == 'hr':
                trend = 5 * np.sin(np.pi * t / self.duration_hours)
            else:
                trend = np.zeros_like(t)
            noise_scale = 0.08
            
        elif self.risk_class == RiskLevel.MODERATE:
            # Clear deteriorating trend (multiple vitals affected)
            if vital == 'lactate':
                trend = 0.8 * t / self.duration_hours  # Linear rise
            elif vital == 'map':
                trend = -8 * t / self.duration_hours   # Linear decline
            elif vital == 'hr':
                trend = 15 * (1 - np.cos(np.pi * t / self.duration_hours))
            elif vital == 'temp':
                trend = 1.5 * np.sin(np.pi * t / self.duration_hours)
            elif vital == 'rr':
                trend = 4 * t / self.duration_hours
            else:
                trend = -2 * t / self.duration_hours
            noise_scale = 0.10
            
        elif self.risk_class == RiskLevel.HIGH:
            # Accelerating deterioration (sepsis emerging)
            if vital == 'lactate':
                trend = 1.5 * (t / self.duration_hours) ** 1.5
            elif vital == 'map':
                trend = -15 * (t / self.duration_hours) ** 1.3
            elif vital == 'hr':
                trend = 25 * (1 - np.cos(1.5 * np.pi * t / self.duration_hours))
            elif vital == 'temp':
                trend = 2.5 * np.sin(1.5 * np.pi * t / self.duration_hours)
            elif vital == 'rr':
                trend = 8 * (t / self.duration_hours) ** 1.2
            elif vital == 'spo2':
                trend = -5 * (t / self.duration_hours) ** 1.5
            else:
                trend = np.zeros_like(t)
            noise_scale = 0.15
            
        else:  # CRITICAL
            # Severe hemodynamic collapse (septic shock)
            if vital == 'lactate':
                trend = 3.0 * (t / self.duration_hours) ** 2
            elif vital == 'map':
                trend = -25 * (t / self.duration_hours) ** 1.5
            elif vital == 'hr':
                trend = 40 * (1 - np.cos(2 * np.pi * t / self.duration_hours))
            elif vital == 'temp':
                trend = 3.0 * np.sin(2 * np.pi * t / self.duration_hours)
            elif vital == 'rr':
                trend = 12 * (t / self.duration_hours) ** 1.3
            elif vital == 'spo2':
                trend = -10 * (t / self.duration_hours) ** 2
            else:
                trend = np.zeros_like(t)
            noise_scale = 0.20
        
        # Add realistic noise
        noise = np.random.normal(0, noise_scale * baseline, len(t))
        
        # Combine baseline + trend + noise
        values = baseline + trend + noise
        
        # Physiological bounds (prevent impossible values)
        if vital == 'lactate':
            values = np.clip(values, 0.5, 10.0)
        elif vital == 'map':
            values = np.clip(values, 40, 120)
        elif vital == 'hr':
            values = np.clip(values, 50, 180)
        elif vital == 'temp':
            values = np.clip(values, 35.0, 41.0)
        elif vital == 'rr':
            values = np.clip(values, 8, 40)
        elif vital == 'spo2':
            values = np.clip(values, 70, 100)
        
        return values
    
    def _add_missing_data(self, values: np.ndarray, missing_rate: float = 0.05) -> np.ndarray:
        """
        Simulate missing measurements (sensor failures, data gaps).
        
        Args:
            values: Original vital sign array
            missing_rate: Fraction of measurements to drop
            
        Returns:
            Array with some values set to NaN
        """
        mask = np.random.random(len(values)) < missing_rate
        values_with_missing = values.copy()
        values_with_missing[mask] = np.nan
        return values_with_missing
    
    def _add_sensor_artifacts(self, values: np.ndarray, artifact_rate: float = 0.02) -> np.ndarray:
        """
        Simulate sensor artifacts (spikes, dropouts).
        
        Args:
            values: Original vital sign array
            artifact_rate: Fraction of measurements to corrupt
            
        Returns:
            Array with occasional artifacts
        """
        artifact_mask = np.random.random(len(values)) < artifact_rate
        artifact_values = values.copy()
        
        # Random spikes (±20% of baseline)
        spikes = np.random.uniform(-0.2, 0.2, len(values)) * values
        artifact_values[artifact_mask] += spikes[artifact_mask]
        
        return artifact_values
    
    def generate(self, include_artifacts: bool = True) -> pd.DataFrame:
        """
        Generate complete patient trajectory.
        
        Args:
            include_artifacts: Whether to add missing data and sensor noise
            
        Returns:
            DataFrame with columns:
            - patient_id, timestamp, lactate, map, hr, temp, rr, spo2, risk_label
        """
        # Generate base timestamp
        start_time = datetime(2026, 1, 1, 0, 0, 0)
        timestamps = [start_time + timedelta(minutes=i * self.interval_min) 
                     for i in range(self.n_measurements)]
        
        # Generate vitals
        vitals = {}
        for vital in self.baseline.keys():
            values = self._generate_progression_pattern(vital)
            
            if include_artifacts:
                values = self._add_sensor_artifacts(values, artifact_rate=0.02)
                values = self._add_missing_data(values, missing_rate=0.05)
            
            vitals[vital] = values
        
        # Create DataFrame
        df = pd.DataFrame({
            'patient_id': self.patient_id,
            'timestamp': timestamps,
            'lactate': vitals['lactate'],
            'map': vitals['map'],
            'hr': vitals['hr'],
            'temp': vitals['temp'],
            'rr': vitals['rr'],
            'spo2': vitals['spo2'],
            'risk_label': int(self.risk_class)
        })
        
        return df


class SyntheticCohortGenerator:
    """
    Generates a cohort of synthetic patients for ML training.
    
    Creates balanced dataset across all 5 risk classes.
    """
    
    def __init__(self, n_patients_per_class: int = 200, duration_hours: int = 12):
        """
        Initialize cohort generator.
        
        Args:
            n_patients_per_class: Number of patients per risk level
            duration_hours: Simulation duration for each patient
        """
        self.n_per_class = n_patients_per_class
        self.duration_hours = duration_hours
        
    def generate_cohort(self, save_path: str = None) -> pd.DataFrame:
        """
        Generate full synthetic patient cohort.
        
        Args:
            save_path: Optional path to save CSV
            
        Returns:
            DataFrame containing all patient trajectories
        """
        all_patients = []
        patient_id = 1
        
        print("=" * 70)
        print("SEWA SYNTHETIC DATA GENERATOR")
        print("=" * 70)
        
        for risk_class in RiskLevel:
            print(f"\nGenerating {self.n_per_class} patients for class: {risk_class.name}")
            
            for i in range(self.n_per_class):
                # Create patient trajectory
                patient = PatientTrajectory(
                    patient_id=patient_id,
                    risk_class=risk_class,
                    duration_hours=self.duration_hours
                )
                
                # Generate data
                df = patient.generate(include_artifacts=True)
                all_patients.append(df)
                
                patient_id += 1
                
                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{self.n_per_class}")
        
        # Combine all patients
        cohort_df = pd.concat(all_patients, ignore_index=True)
        
        # Shuffle rows (important for train/test split later)
        cohort_df = cohort_df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        print("\n" + "=" * 70)
        print("COHORT GENERATION COMPLETE")
        print("=" * 70)
        print(f"Total patients: {patient_id - 1}")
        print(f"Total measurements: {len(cohort_df):,}")
        print(f"Time range: {cohort_df['timestamp'].min()} to {cohort_df['timestamp'].max()}")
        print("\nClass distribution:")
        print(cohort_df.groupby('risk_label')['patient_id'].nunique())
        print("\nMissing data statistics:")
        print(cohort_df.isnull().sum())
        
        # Save if path provided
        if save_path:
            cohort_df.to_csv(save_path, index=False)
            print(f"\n✓ Saved to: {save_path}")
        
        return cohort_df
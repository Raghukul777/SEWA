#!/usr/bin/env python3
"""
SEWA Integration Test Script

Tests complete SEWA pipeline with simulated deteriorating patient.
Usage: python test_system.py [--model-path models/sewa_risk_model.pkl]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sewa.trend_engine import TrendRecognitionEngine
from sewa.ml_pipeline import SEWARiskModel
from sewa.core_system import SEWASystem, PatientState


def main():
    parser = argparse.ArgumentParser(
        description='Test SEWA system integration'
    )
    parser.add_argument(
        '--model-path',
        type=str,
        default='models/sewa_risk_model.pkl',
        help='Path to trained model (default: models/sewa_risk_model.pkl)'
    )
    
    args = parser.parse_args()
    
    # Check if model exists
    if not Path(args.model_path).exists():
        print(f"Error: Model not found at {args.model_path}")
        print("Run train_model.py first to create the model")
        sys.exit(1)
    
    print("=" * 70)
    print("SEWA INTEGRATION TEST")
    print("=" * 70)
    print("\nScenario: Patient deteriorating from stable to septic shock over 8 hours")
    print(f"Model: {args.model_path}")
    print()
    
    # Initialize components
    vitals = ['lactate', 'map', 'hr', 'temp', 'rr', 'spo2']
    trend_engine = TrendRecognitionEngine(vital_names=vitals)
    
    print("Loading trained model...")
    ml_model = SEWARiskModel.load(args.model_path)
    print(f"✓ Model loaded ({ml_model.model_type})")
    
    # Initialize SEWA
    sewa = SEWASystem(
        trend_engine=trend_engine,
        ml_model=ml_model,
        patient_id="TEST-PT-001"
    )
    
    # Simulate 8 hours of patient deterioration
    start_time = datetime(2026, 1, 18, 8, 0, 0)
    
    test_timeline = [
        # Hour 0: Baseline (stable)
        (0, PatientState(
            timestamp=start_time,
            lactate=1.4, map=76, hr=82, temp=37.1, rr=16, spo2=98,
            on_vasopressors=False, infection_suspected=False
        )),
        
        # Hour 1: Still stable
        (1, PatientState(
            timestamp=start_time + timedelta(hours=1),
            lactate=1.5, map=75, hr=84, temp=37.3, rr=16, spo2=98,
            on_vasopressors=False, infection_suspected=False
        )),
        
        # Hour 2: Early signs (infection suspected)
        (2, PatientState(
            timestamp=start_time + timedelta(hours=2),
            lactate=1.8, map=73, hr=92, temp=37.9, rr=18, spo2=97,
            on_vasopressors=False, infection_suspected=True
        )),
        
        # Hour 3: WATCH level
        (3, PatientState(
            timestamp=start_time + timedelta(hours=3),
            lactate=2.1, map=71, hr=98, temp=38.2, rr=20, spo2=96,
            on_vasopressors=False, infection_suspected=True
        )),
        
        # Hour 4: MODERATE deterioration
        (4, PatientState(
            timestamp=start_time + timedelta(hours=4),
            lactate=2.6, map=68, hr=104, temp=38.6, rr=22, spo2=95,
            on_vasopressors=False, infection_suspected=True
        )),
        
        # Hour 5: HIGH risk
        (5, PatientState(
            timestamp=start_time + timedelta(hours=5),
            lactate=3.2, map=64, hr=112, temp=38.9, rr=25, spo2=93,
            on_vasopressors=False, infection_suspected=True
        )),
        
        # Hour 6: Vasopressors started
        (6, PatientState(
            timestamp=start_time + timedelta(hours=6),
            lactate=3.8, map=61, hr=118, temp=39.2, rr=28, spo2=92,
            on_vasopressors=True, infection_suspected=True
        )),
        
        # Hour 7: CRITICAL / Septic shock
        (7, PatientState(
            timestamp=start_time + timedelta(hours=7),
            lactate=4.5, map=56, hr=126, temp=39.5, rr=30, spo2=90,
            on_vasopressors=True, infection_suspected=True
        )),
        
        # Hour 8: Severe septic shock
        (8, PatientState(
            timestamp=start_time + timedelta(hours=8),
            lactate=5.2, map=52, hr=132, temp=39.8, rr=32, spo2=88,
            on_vasopressors=True, infection_suspected=True
        )),
    ]
    
    # Process each measurement
    alerts_generated = []
    
    for hour, patient_state in test_timeline:
        print(f"\n{'='*70}")
        print(f"HOUR {hour}: {patient_state.timestamp.strftime('%H:%M')}")
        print(f"{'='*70}")
        print(f"Vitals:")
        print(f"  Lactate: {patient_state.lactate:.1f} mmol/L")
        print(f"  MAP: {patient_state.map:.0f} mmHg")
        print(f"  HR: {patient_state.hr:.0f} bpm")
        print(f"  Temp: {patient_state.temp:.1f}°C")
        print(f"  RR: {patient_state.rr:.0f} breaths/min")
        print(f"  SpO2: {patient_state.spo2:.0f}%")
        print(f"  Vasopressors: {'Yes' if patient_state.on_vasopressors else 'No'}")
        
        # Process measurement
        alert = sewa.process_measurement(patient_state)
        
        if alert:
            alerts_generated.append(alert)
            print(f"\n🚨 ALERT GENERATED")
            print(f"├─ ML Risk: {alert.ml_risk_level.name}")
            print(f"├─ Final Risk: {alert.final_risk_level.name} (score: {alert.risk_score:.2f})")
            
            if alert.override_applied:
                print(f"├─ Override: YES")
                print(f"│  └─ {alert.override_reason}")
            else:
                print(f"├─ Override: No")
            
            if alert.rules_triggered:
                print(f"├─ Rules: {', '.join(alert.rules_triggered)}")
            
            print(f"├─ Action: {alert.recommended_action.name}")
            
            if alert.key_trends:
                print(f"├─ Trends:")
                for trend in alert.key_trends:
                    print(f"│  • {trend}")
            
            if alert.concerning_vitals:
                print(f"├─ Concerning Vitals:")
                for vital in alert.concerning_vitals:
                    print(f"│  • {vital}")
            
            print(f"└─ Clinical Narrative:")
            print(f"   {alert.clinical_narrative}")
        else:
            print(f"\n✓ No alert (risk below threshold)")
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"\nTotal measurements processed: {len(test_timeline)}")
    print(f"Alerts generated: {len(alerts_generated)}")
    
    if alerts_generated:
        print(f"\nAlert timeline:")
        for alert in alerts_generated:
            hour = (alert.timestamp - start_time).total_seconds() / 3600
            print(f"  Hour {hour:.0f}: {alert.final_risk_level.name} "
                  f"(action: {alert.recommended_action.name})")
    
    # Validate expected behavior
    print(f"\n{'='*70}")
    print("VALIDATION CHECKS")
    print(f"{'='*70}")
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Should generate alerts
    checks_total += 1
    if len(alerts_generated) >= 5:
        print("✓ Alert generation working (≥5 alerts)")
        checks_passed += 1
    else:
        print(f"✗ Alert generation issue (only {len(alerts_generated)} alerts)")
    
    # Check 2: Risk should escalate over time
    checks_total += 1
    if alerts_generated:
        risk_levels = [a.final_risk_level for a in alerts_generated]
        if risk_levels[-1] >= risk_levels[0]:
            print("✓ Risk escalation working")
            checks_passed += 1
        else:
            print("✗ Risk not escalating as expected")
    
    # Check 3: Should reach CRITICAL by end
    checks_total += 1
    if alerts_generated and alerts_generated[-1].final_risk_level.name == 'CRITICAL':
        print("✓ CRITICAL risk detected for septic shock")
        checks_passed += 1
    else:
        print("✗ Did not reach CRITICAL risk")
    
    # Check 4: Rules should trigger
    checks_total += 1
    any_rules = any(a.rules_triggered for a in alerts_generated)
    if any_rules:
        print("✓ Clinical rules triggering")
        checks_passed += 1
    else:
        print("✗ No rules triggered (check rule engine)")
    
    print(f"\n{'='*70}")
    print(f"RESULT: {checks_passed}/{checks_total} checks passed")
    print(f"{'='*70}\n")
    
    if checks_passed == checks_total:
        print("✓ All integration tests PASSED")
        print("SEWA system is functioning correctly")
        sys.exit(0)
    else:
        print("⚠ Some checks FAILED - review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
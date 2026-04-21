"""
SEWA Alert Pipeline Diagnostic Test
Tests the full alert-generation flow end-to-end in-process:
  1. Loads synthetic patients from CSV
  2. Reads a vital from the simulator for each patient
  3. Runs the ML engine + rule engine on those vitals
  4. Calls _persist_and_assess() — the exact same function the WS stream calls
  5. Reports whether an alert was created or suppressed (30-min window)
"""
import time
from datetime import datetime
from pathlib import Path

# Bootstrap data loader (must be done before simulator imports)
from api.data_loader import initialize_data_loader
initialize_data_loader(Path("data/synthetic_patients.csv"))

from api.database import SessionLocal, Patient, Alert
from api.simulator import get_next_reading
from api.vitals import _run_rule_based_risk
from api.ws import _persist_and_assess

def run():
    db = SessionLocal()
    patients = db.query(Patient).all()
    db.close()

    print(f"\n{'='*55}")
    print(f"  ALERT PIPELINE TEST — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")
    print(f"Patients in DB: {len(patients)}")
    for p in patients:
        print(f"  {p.patient_id} | {p.name} | synthetic_id={p.synthetic_data_id}")

    print()
    for patient in patients:
        pid = patient.patient_id
        print(f"\n--- {pid} ({patient.name}) ---")

        # Step 1: Read vitals from simulator
        t0 = time.time()
        vitals = get_next_reading(pid)
        t_vitals = (time.time() - t0) * 1000
        print(f"  Vitals  ({t_vitals:.1f}ms): HR={vitals.get('heart_rate')}, RR={vitals.get('respiratory_rate')}, "
              f"Temp={vitals.get('temperature')}, SpO2={vitals.get('spo2')}, "
              f"Lac={vitals.get('lactate')}, MAP={vitals.get('map')}")

        # Step 2: Quick rule-engine preview
        from datetime import datetime as dt
        fake_reading = type('R', (), {
            'heart_rate': vitals.get('heart_rate'),
            'respiratory_rate': vitals.get('respiratory_rate'),
            'temperature': vitals.get('temperature'),
            'spo2': vitals.get('spo2'),
            'lactate': vitals.get('lactate'),
            'map': vitals.get('map'),
            'wbc': vitals.get('wbc'),
            'creatinine': vitals.get('creatinine'),
            'timestamp': dt.utcnow()
        })()
        rule_risk = _run_rule_based_risk([fake_reading])
        print(f"  Rule Engine: risk={rule_risk['riskLevel']} -> {rule_risk['summary']}")

        # Step 3: Full persist + ML assess (exactly what WS does)
        t0 = time.time()
        reading_dict, alert_dict = _persist_and_assess(pid, vitals)
        t_total = (time.time() - t0) * 1000
        print(f"  persist_and_assess ({t_total:.1f}ms):")

        if alert_dict:
            print(f"  ✅ ALERT CREATED! risk={alert_dict['risk_level']} | {alert_dict['clinical_summary']}")
        else:
            # Check if suppressed by 30-min window
            from datetime import timedelta
            db2 = SessionLocal()
            cutoff = dt.utcnow() - timedelta(minutes=30)
            recent = db2.query(Alert).filter(
                Alert.patient_id == pid,
                Alert.timestamp >= cutoff
            ).all()
            db2.close()
            if recent:
                print(f"  🔕 SUPPRESSED by 30-min window. Existing alerts: {[(a.risk_level, str(a.timestamp)) for a in recent]}")
            else:
                print(f"  ℹ️  No alert. Risk level was: (check rule engine above) — may be LOW")

    print(f"\n{'='*55}")

if __name__ == "__main__":
    run()

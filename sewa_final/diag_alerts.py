"""Diagnose alert generation pipeline inline"""
import json, sys
from pathlib import Path
from datetime import datetime, timedelta

from api.data_loader import initialize_data_loader
initialize_data_loader(Path("data/synthetic_patients.csv"))

from api.database import SessionLocal, Patient, Alert, VitalReading
from api.simulator import get_next_reading
from api.vitals import _run_rule_based_risk
from api.ws import _persist_and_assess

results = []

db = SessionLocal()
patients = db.query(Patient).all()
all_alerts = db.query(Alert).order_by(Alert.timestamp.desc()).limit(10).all()
db.close()

patient_summary = [{"id": p.patient_id, "name": p.name, "synth_id": p.synthetic_data_id} for p in patients]

for p in patients:
    pid = p.patient_id
    v = get_next_reading(pid)

    # simulate rule engine with simple check
    hr = v.get("heart_rate")
    rr = v.get("respiratory_rate")
    temp = v.get("temperature")
    spo2 = v.get("spo2")
    lac = v.get("lactate")
    mapp = v.get("map")

    # SIRS criteria count
    sirs = 0
    if hr and hr > 90: sirs += 1
    if rr and rr > 20: sirs += 1
    if temp and (temp > 38.3 or temp < 36): sirs += 1
    if lac and lac > 2: sirs += 1

    reading_dict, alert_dict = _persist_and_assess(pid, v)

    # check suppression
    db2 = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    recent_alerts = db2.query(Alert).filter(Alert.patient_id == pid, Alert.timestamp >= cutoff).all()
    db2.close()

    results.append({
        "patient_id": pid,
        "vitals": {"hr": hr, "rr": rr, "temp": temp, "spo2": spo2, "lac": lac, "map": mapp},
        "sirs_count": sirs,
        "alert_generated": alert_dict is not None,
        "alert_risk": alert_dict["risk_level"] if alert_dict else None,
        "alert_summary": alert_dict["clinical_summary"] if alert_dict else None,
        "suppressed_by_30min_window": len(recent_alerts) > 0,
        "existing_alerts_in_30min": [{"risk": a.risk_level, "time": str(a.timestamp)} for a in recent_alerts]
    })

recent_db_alerts = []
db3 = SessionLocal()
for a in db3.query(Alert).order_by(Alert.timestamp.desc()).limit(5).all():
    recent_db_alerts.append({
        "id": a.id,
        "patient_id": a.patient_id,
        "risk_level": a.risk_level,
        "is_active": a.is_active,
        "feedback": a.feedback,
        "timestamp": str(a.timestamp)
    })
db3.close()

final = {
    "patients": patient_summary,
    "pipeline_results": results,
    "recent_db_alerts": recent_db_alerts
}

with open("diag_result.json", "w") as f:
    json.dump(final, f, indent=2)

print("DONE")

"""Run 5 vitals cycles and save results to JSON"""
import time, json
from api.data_loader import initialize_data_loader
from pathlib import Path
initialize_data_loader(Path("data/synthetic_patients.csv"))

from api.ws import _persist_and_assess
from api.simulator import get_next_reading

pids = ["P-53222", "P-6100B", "P-E4C16"]
all_results = []

for cycle in range(1, 8):
    cycle_results = {"cycle": cycle, "patients": []}
    for pid in pids:
        v = get_next_reading(pid)
        _, alert_dict = _persist_and_assess(pid, v)
        cycle_results["patients"].append({
            "pid": pid,
            "hr": round(v.get("heart_rate") or 0, 1),
            "rr": round(v.get("respiratory_rate") or 0, 1),
            "map": round(v.get("map") or 0, 1),
            "lac": round(v.get("lactate") or 0, 2),
            "alert": alert_dict["risk_level"] if alert_dict else None,
            "alert_summary": alert_dict["clinical_summary"] if alert_dict else None
        })
    all_results.append(cycle_results)
    time.sleep(0.1)

with open("cycles_result.json", "w") as f:
    json.dump(all_results, f, indent=2)
print("SAVED")

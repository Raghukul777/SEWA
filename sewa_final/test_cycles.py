"""Run 5 vitals cycles rapidly to trigger alert thresholds"""
import time
from api.data_loader import initialize_data_loader
from pathlib import Path
initialize_data_loader(Path("data/synthetic_patients.csv"))

from api.ws import _persist_and_assess
from api.simulator import get_next_reading

pids = ["P-53222", "P-6100B", "P-E4C16"]

print("Running 5 reading cycles for all patients...\n")
for cycle in range(1, 6):
    print(f"=== Cycle {cycle} ===")
    for pid in pids:
        v = get_next_reading(pid)
        hr = v.get("heart_rate")
        rr = v.get("respiratory_rate")
        mmap = v.get("map")
        lac = v.get("lactate")
        _, alert_dict = _persist_and_assess(pid, v)
        status = f"ALERT: {alert_dict['risk_level']}!" if alert_dict else "No alert"
        print(f"  {pid}: HR={round(hr,1) if hr else 'N/A'}, RR={round(rr,1) if rr else 'N/A'}, MAP={round(mmap,1) if mmap else 'N/A'}, Lac={round(lac,2) if lac else 'N/A'} -> {status}")
    time.sleep(0.1)

print("\nDone. Check your Live Alerts panel!")

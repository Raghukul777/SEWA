"""Test vitals after remapping to critical synthetic IDs"""
from api.data_loader import initialize_data_loader, reset_patient_index
from pathlib import Path
initialize_data_loader(Path("data/synthetic_patients.csv"))

# Reset read indexes so all 3 patients start from beginning of new data
for sid in [927, 934, 845]:
    reset_patient_index(sid)

from api.simulator import get_next_reading
from api.ws import _persist_and_assess

pids = ["P-53222", "P-6100B", "P-E4C16"]
for pid in pids:
    v = get_next_reading(pid)
    hr = v.get("heart_rate")
    rr = v.get("respiratory_rate")
    mmap = v.get("map")
    lac = v.get("lactate")
    temp = v.get("temperature")
    print(f"\n{pid}: HR={hr}, RR={rr}, MAP={mmap}, Lac={lac}, Temp={temp}")

    reading_dict, alert_dict = _persist_and_assess(pid, v)
    if alert_dict:
        print(f"  ALERT: {alert_dict['risk_level']} | {alert_dict['clinical_summary']}")
    else:
        print("  No alert this cycle (may need more readings to build trends)")

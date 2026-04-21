import time, json
from api.ml.inference.risk_engine import CoreMLEngine
from api.schemas import VitalSigns

def test():
    t0 = time.time()
    engine = CoreMLEngine()
    t1 = time.time()
    print(f"Engine Init Time: {(t1 - t0) * 1000:.2f} ms")

    vitals = VitalSigns(
        patient_id="TEST-1",
        heart_rate=145.0,
        systolic_bp=75.0,
        diastolic_bp=40.0,
        temperature_c=39.5,
        respiratory_rate=30.0,
        lactate=5.5,
        wbc_count=22.0
    )

    t0_inf = time.time()
    alert = engine.predict(vitals)
    t1_inf = time.time()

    print("\n--- RESULTS ---")
    print(f"Inference Time : {(t1_inf - t0_inf) * 1000:.2f} ms")
    print(f"Risk Level     : {alert.risk_level}")
    print(f"Risk Score     : {alert.risk_score:.4f}")
    print(f"ML Probability : {alert.ml_probability:.4f}")
    print(f"Overrides      : {alert.rule_overrides}")
    print(f"System Health  : {alert.system_health}")

if __name__ == "__main__":
    test()

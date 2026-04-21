"""
SEWA — Feature Configuration
Defines MIMIC-III item-ID mappings and feature group definitions
for the 60-feature vector.
"""

# ─── MIMIC-III CHARTEVENTS Item IDs ───────────────────────────────────
VITAL_ITEM_IDS = {
    211:    "heart_rate",
    220045: "heart_rate",
    618:    "respiratory_rate",
    220210: "respiratory_rate",
    223761: "temperature_f",      # Fahrenheit → convert to Celsius
    678:    "temperature_f",
    223762: "temperature_c",
    676:    "temperature_c",
    51:     "systolic_bp",
    220179: "systolic_bp",
    455:    "systolic_bp",
    8368:   "diastolic_bp",
    220180: "diastolic_bp",
    8441:   "diastolic_bp",
    646:    "spo2_percent",
    220277: "spo2_percent",
}

# ─── MIMIC-III LABEVENTS Item IDs ─────────────────────────────────────
LAB_ITEM_IDS = {
    51300: "wbc_count",
    51301: "wbc_count",
    50813: "lactate",
    50912: "creatinine",
    50885: "bilirubin_total",
    51006: "bun",
    50931: "glucose",
    50809: "glucose",
    51222: "hemoglobin",
    51265: "platelets",
}

# ─── Feature Group Definitions ────────────────────────────────────────

GROUP_A_RAW_VITALS = [
    "heart_rate", "respiratory_rate", "temperature_c",
    "systolic_bp", "diastolic_bp", "spo2_percent",
]

GROUP_B_RAW_LABS = [
    "wbc_count", "lactate", "creatinine", "bilirubin_total",
    "bun", "glucose", "hemoglobin", "platelets",
]

# Group C — Vital trends (6 features × 3 vitals = 18)
TREND_VITALS = ["heart_rate", "respiratory_rate", "temperature_c"]
TREND_SUFFIXES = [
    "_lag_1h", "_lag_2h",
    "_roll_mean_4h", "_roll_std_4h",
    "_trend_slope", "_delta_from_baseline",
]

GROUP_C_VITAL_TRENDS = [
    f"{v}{s}" for v in TREND_VITALS for s in TREND_SUFFIXES
]

# Group D — Lab trends (2 features × 4 labs = 8)
TREND_LABS = ["wbc_count", "lactate", "creatinine", "bilirubin_total"]

GROUP_D_LAB_TRENDS = [
    f"{lab}{s}" for lab in TREND_LABS for s in ("_delta_24h", "_trend")
]

# Group E — Clinical scores (6)
GROUP_E_CLINICAL_SCORES = [
    "sirs_score", "qsofa_score",
    "sofa_respiratory", "sofa_coagulation",
    "sofa_liver", "sofa_renal",
]

# Group F — Time features (4)
GROUP_F_TIME = [
    "hours_since_admission",
    "time_since_last_vital_hours",
    "time_since_last_lab_hours",
    "is_night_shift",
]

# Group G — Admission context (one-hot, ~10)
ADMISSION_TYPES = ["EMERGENCY", "ELECTIVE", "URGENT"]
CARE_UNITS = ["MICU", "SICU", "CCU", "CVICU", "NICU", "TSICU", "other"]

GROUP_G_ADMISSION = (
    [f"admission_type_{t}" for t in ADMISSION_TYPES]
    + [f"care_unit_{u}" for u in CARE_UNITS]
)

# ─── Complete ordered feature list (60 features) ─────────────────────
ALL_FEATURES = (
    GROUP_A_RAW_VITALS
    + GROUP_B_RAW_LABS
    + GROUP_C_VITAL_TRENDS
    + GROUP_D_LAB_TRENDS
    + GROUP_E_CLINICAL_SCORES
    + GROUP_F_TIME
    + GROUP_G_ADMISSION
)

assert len(ALL_FEATURES) == 60, f"Expected 60 features, got {len(ALL_FEATURES)}"

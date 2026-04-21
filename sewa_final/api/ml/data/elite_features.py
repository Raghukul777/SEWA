"""
SEWA — Elite Feature Engineering
=================================
Advanced clinical features for top-tier sepsis prediction:
  - Derived vitals: MAP, shock index, pulse pressure
  - Missingness indicators (clinically informative)
  - Rolling windows: 6h, 12h, 24h (max, min, mean, std)
  - Trend acceleration (2nd derivative)
  - Interaction features (lactate × HR, etc.)
  - T-6h label shift for early warning
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
import structlog

logger = structlog.get_logger(__name__)

# ── Column rename (PhysioNet 2019 → SEWA) ─────────────────────────────
RENAME_MAP = {
    "HR": "heart_rate", "Resp": "respiratory_rate",
    "Temp": "temperature_c", "SBP": "systolic_bp",
    "DBP": "diastolic_bp", "O2Sat": "spo2_percent",
    "WBC": "wbc_count", "Lactate": "lactate",
    "Creatinine": "creatinine", "Bilirubin_total": "bilirubin_total",
    "BUN": "bun", "Glucose": "glucose",
    "Hgb": "hemoglobin", "Platelets": "platelets",
    "ICULOS": "hours_since_admission",
    "Patient_ID": "HADM_ID", "SepsisLabel": "label",
    "FiO2": "fio2", "pH": "ph", "PaCO2": "paco2",
    "HCO3": "hco3", "BaseExcess": "base_excess",
    "Age": "age", "Gender": "gender",
    "Unit1": "unit_micu", "Unit2": "unit_sicu",
    "HospAdmTime": "hosp_adm_time",
}

VITAL_COLS = ["heart_rate", "respiratory_rate", "temperature_c",
              "systolic_bp", "diastolic_bp", "spo2_percent"]
LAB_COLS   = ["wbc_count", "lactate", "creatinine", "bilirubin_total",
              "bun", "glucose", "hemoglobin", "platelets"]
ALL_BASE   = VITAL_COLS + LAB_COLS

WINDOWS    = [6, 12, 24]          # rolling window sizes (hours)
TREND_VITALS = ["heart_rate", "respiratory_rate", "temperature_c"]
TREND_LABS   = ["wbc_count", "lactate", "creatinine", "bilirubin_total"]


# ── Clinical score helpers ─────────────────────────────────────────────
def _sirs(row):
    s = 0
    if pd.notna(row.get("temperature_c")):
        s += int(row["temperature_c"] > 38.3 or row["temperature_c"] < 36.0)
    if pd.notna(row.get("heart_rate")):      s += int(row["heart_rate"] > 90)
    if pd.notna(row.get("respiratory_rate")): s += int(row["respiratory_rate"] > 20)
    if pd.notna(row.get("wbc_count")):       s += int(row["wbc_count"] > 12 or row["wbc_count"] < 4)
    return s

def _qsofa(row):
    s = 0
    if pd.notna(row.get("respiratory_rate")): s += int(row["respiratory_rate"] >= 22)
    if pd.notna(row.get("systolic_bp")):      s += int(row["systolic_bp"] <= 100)
    return s

def _sofa_resp(v):   return 0 if pd.isna(v) else (0 if v>=96 else 1 if v>=92 else 2 if v>=88 else 3 if v>=80 else 4)
def _sofa_coag(v):   return 0 if pd.isna(v) else (0 if v>=150 else 1 if v>=100 else 2 if v>=50 else 3 if v>=20 else 4)
def _sofa_liver(v):  return 0 if pd.isna(v) else (0 if v<1.2 else 1 if v<2.0 else 2 if v<6.0 else 3 if v<12.0 else 4)
def _sofa_renal(v):  return 0 if pd.isna(v) else (0 if v<1.2 else 1 if v<2.0 else 2 if v<3.5 else 3 if v<5.0 else 4)


# ── Per-patient temporal feature engineering ───────────────────────────
def _engineer_patient(grp: pd.DataFrame) -> pd.DataFrame:
    grp = grp.sort_values("hours_since_admission").copy()
    n   = len(grp)

    # ── 1. Missingness indicators ─────────────────────────────────────
    for col in ALL_BASE:
        if col in grp.columns:
            grp[f"{col}_missing"] = grp[col].isna().astype(np.int8)

    # ── 2. Population-median impute (within patient first) ───────────
    for col in ALL_BASE:
        if col in grp.columns and grp[col].isna().any():
            pm = grp[col].median()
            grp[col] = grp[col].fillna(pm)

    # ── 3. Derived clinical features ──────────────────────────────────
    sbp = grp.get("systolic_bp", pd.Series(np.nan, index=grp.index))
    dbp = grp.get("diastolic_bp", pd.Series(np.nan, index=grp.index))
    hr  = grp.get("heart_rate", pd.Series(np.nan, index=grp.index))
    lac = grp.get("lactate", pd.Series(np.nan, index=grp.index))
    spo = grp.get("spo2_percent", pd.Series(np.nan, index=grp.index))
    fio = grp.get("fio2", pd.Series(np.nan, index=grp.index))

    grp["map"]             = (sbp + 2 * dbp) / 3
    grp["pulse_pressure"]  = sbp - dbp
    grp["shock_index"]     = hr / sbp.replace(0, np.nan)
    grp["lactate_x_hr"]    = lac * hr            # distributive shock proxy
    grp["spo2_fio2_ratio"] = spo / fio.replace(0, np.nan)  # lung injury

    # ── 4. Rolling windows (6h, 12h, 24h) ────────────────────────────
    for col in ALL_BASE + ["map", "shock_index"]:
        if col not in grp.columns:
            continue
        vals = grp[col].values.astype(float)
        for w in WINDOWS:
            roll_max  = np.full(n, np.nan)
            roll_min  = np.full(n, np.nan)
            roll_mean = np.full(n, np.nan)
            roll_std  = np.full(n, np.nan)
            for i in range(n):
                # hours_since_admission is the time index
                t_now   = grp["hours_since_admission"].iloc[i]
                mask    = (grp["hours_since_admission"] >= t_now - w) & \
                          (grp["hours_since_admission"] <= t_now)
                window  = vals[mask.values]
                valid   = window[~np.isnan(window)]
                if len(valid) > 0:
                    roll_max[i]  = valid.max()
                    roll_min[i]  = valid.min()
                    roll_mean[i] = valid.mean()
                    roll_std[i]  = valid.std() if len(valid) > 1 else 0.0
            grp[f"{col}_max_{w}h"]  = roll_max
            grp[f"{col}_min_{w}h"]  = roll_min
            grp[f"{col}_mean_{w}h"] = roll_mean
            grp[f"{col}_std_{w}h"]  = roll_std

    # ── 5. Trend & acceleration ───────────────────────────────────────
    for col in TREND_VITALS + TREND_LABS:
        if col not in grp.columns:
            continue
        vals = grp[col].values.astype(float)
        delta      = np.full(n, 0.0)
        slope      = np.full(n, 0.0)
        accel      = np.full(n, 0.0)
        delta_24h  = np.full(n, 0.0)

        for i in range(1, n):
            delta[i] = vals[i] - vals[i - 1]
        for i in range(1, n):
            accel[i] = delta[i] - delta[i - 1]

        for i in range(n):
            window = vals[max(0, i-3): i+1]
            v = window[~np.isnan(window)]
            if len(v) >= 2:
                slope[i] = scipy_stats.linregress(np.arange(len(v)), v).slope

            # 24h delta
            t_now = grp["hours_since_admission"].iloc[i]
            mask24 = (grp["hours_since_admission"] <= t_now - 24)
            if mask24.any():
                old = vals[mask24.values][-1]
                if not np.isnan(old) and not np.isnan(vals[i]):
                    delta_24h[i] = vals[i] - old

        grp[f"{col}_delta"]        = delta
        grp[f"{col}_trend_slope"]  = slope
        grp[f"{col}_acceleration"] = accel
        grp[f"{col}_delta_24h"]    = delta_24h

    # ── 6. Time-since-last-abnormal ───────────────────────────────────
    ABNORMAL = {
        "heart_rate":        lambda v: v > 90 or v < 50,
        "respiratory_rate":  lambda v: v > 20,
        "temperature_c":     lambda v: v > 38.3 or v < 36.0,
        "systolic_bp":       lambda v: v < 90,
        "lactate":           lambda v: v > 2.0,
        "spo2_percent":      lambda v: v < 92,
    }
    for col, fn in ABNORMAL.items():
        if col not in grp.columns:
            continue
        hrs = grp["hours_since_admission"].values
        vals = grp[col].values
        time_since = np.full(n, np.nan)
        last_abn_t = np.nan
        for i in range(n):
            if not np.isnan(vals[i]) and fn(vals[i]):
                last_abn_t = hrs[i]
            time_since[i] = hrs[i] - last_abn_t if not np.isnan(last_abn_t) else 999.0
        grp[f"{col}_hrs_since_abnormal"] = time_since

    return grp


def _compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized SIRS, qSOFA, SOFA component scores."""
    df["sirs_score"]       = df.apply(_sirs,  axis=1)
    df["qsofa_score"]      = df.apply(_qsofa, axis=1)
    df["sofa_respiratory"] = df["spo2_percent"].apply(_sofa_resp)  if "spo2_percent"   in df.columns else 0
    df["sofa_coagulation"] = df["platelets"].apply(_sofa_coag)     if "platelets"       in df.columns else 0
    df["sofa_liver"]       = df["bilirubin_total"].apply(_sofa_liver) if "bilirubin_total" in df.columns else 0
    df["sofa_renal"]       = df["creatinine"].apply(_sofa_renal)   if "creatinine"      in df.columns else 0
    df["sofa_total"]       = (df["sofa_respiratory"] + df["sofa_coagulation"] +
                               df["sofa_liver"] + df["sofa_renal"])
    return df


def rule_engine_overlay(ml_prob: float, row: dict) -> float:
    """
    Clinical hard-override + boost layer on top of ML probability.
    Ensures textbook sepsis cases are never under-flagged.
    """
    qsofa   = row.get("qsofa_score",   0) or 0
    sirs    = row.get("sirs_score",    0) or 0
    sofa    = row.get("sofa_total",    0) or 0
    lactate = row.get("lactate",       0) or 0
    sbp     = row.get("systolic_bp", 120) or 120

    # Hard override: severe sepsis indicators
    if sofa >= 3 and lactate > 2.0:
        return max(ml_prob, 0.92)
    if qsofa >= 2 and lactate > 2.0:
        return max(ml_prob, 0.88)
    if sbp < 70:
        return max(ml_prob, 0.90)            # septic shock threshold

    # Boost: SIRS + ML agreement
    if sirs >= 3 and ml_prob > 0.45:
        return min(ml_prob * 1.15, 0.99)
    if qsofa >= 2 and ml_prob > 0.40:
        return min(ml_prob * 1.10, 0.99)

    return float(ml_prob)


def load_and_engineer(
    csv_path,
    missing_threshold: float = 0.60,
    label_shift_hours: int   = 6,
) -> pd.DataFrame:
    """
    Full elite feature pipeline.

    Parameters
    ----------
    csv_path : path to PhysioNet/Kaggle Dataset.csv
    missing_threshold : drop rows with > this fraction vital/lab NaN
    label_shift_hours : predict sepsis N hours ahead (0 = current)

    Returns
    -------
    DataFrame ready for model training with 'label' and 'HADM_ID'
    """
    import pandas as pd
    from pathlib import Path

    logger.info("elite_pipeline_start", path=str(csv_path))
    df = pd.read_csv(csv_path, low_memory=False)
    df.rename(columns=RENAME_MAP, inplace=True)
    logger.info("raw_shape", rows=len(df), cols=len(df.columns))

    # ── T-6h label shift ─────────────────────────────────────────────
    if label_shift_hours > 0 and "label" in df.columns and "HADM_ID" in df.columns:
        logger.info("applying_label_shift", hours=label_shift_hours)
        def shift_labels(grp):
            g = grp.sort_values("hours_since_admission").copy()
            g["label"] = g["label"].rolling(
                window=label_shift_hours + 1, min_periods=1
            ).max().shift(-label_shift_hours).fillna(0)
            return g
        df = df.groupby("HADM_ID", group_keys=False).apply(shift_labels)
        df["label"] = df["label"].astype(int)

    # ── Drop high-missing rows ───────────────────────────────────────
    key = [c for c in ALL_BASE if c in df.columns]
    before = len(df)
    df = df[df[key].isna().mean(axis=1) <= missing_threshold].copy()
    logger.info("dropped_high_missing", dropped=before - len(df), remaining=len(df))

    # ── Per-patient feature engineering ─────────────────────────────
    logger.info("engineering_features_per_patient")
    df = df.groupby("HADM_ID", group_keys=False).apply(_engineer_patient)

    # ── Clinical scores ──────────────────────────────────────────────
    df = _compute_scores(df)

    # ── Admission context ────────────────────────────────────────────
    df["care_unit_micu"]  = df.get("unit_micu", pd.Series(0, index=df.index)).fillna(0).astype(int)
    df["care_unit_sicu"]  = df.get("unit_sicu", pd.Series(0, index=df.index)).fillna(0).astype(int)
    df["care_unit_other"] = ((df["care_unit_micu"] == 0) & (df["care_unit_sicu"] == 0)).astype(int)
    df["admission_type_EMERGENCY"] = 1

    # ── Fill remaining NaN ───────────────────────────────────────────
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    logger.info("elite_pipeline_done", shape=df.shape,
                sepsis_rate=round(df["label"].mean(), 4) if "label" in df.columns else "N/A")
    return df


def get_feature_columns(df: pd.DataFrame) -> list:
    """Return all feature columns (exclude meta-columns)."""
    exclude = {"HADM_ID", "label", "hours_since_admission",
               "unit_micu", "unit_sicu", "hosp_adm_time",
               "age", "gender", "fio2", "ph", "paco2",
               "hco3", "base_excess"}
    return [c for c in df.select_dtypes(include=[np.number]).columns
            if c not in exclude]


def split_by_patient(df, train_frac=0.70, val_frac=0.15, random_state=42):
    ids = df["HADM_ID"].unique()
    rng = np.random.default_rng(random_state)
    rng.shuffle(ids)
    n  = len(ids)
    n1 = int(n * train_frac)
    n2 = int(n * val_frac)
    train_df = df[df["HADM_ID"].isin(ids[:n1])].copy()
    val_df   = df[df["HADM_ID"].isin(ids[n1:n1+n2])].copy()
    test_df  = df[df["HADM_ID"].isin(ids[n1+n2:])].copy()
    logger.info("patient_split", train=len(train_df), val=len(val_df), test=len(test_df))
    return train_df, val_df, test_df

"""
SEWA — Data Cleaning Pipeline
Sequential cleaning steps applied to MIMIC-III extracted data.
Enforces train-only fitting for scaler and IQR bounds.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler
import structlog

logger = structlog.get_logger(__name__)

ARTIFACTS_DIR = Path("app/ml/artifacts")

# ─── Admission type and care unit categories for one-hot encoding ─────
ADMISSION_TYPES = ["EMERGENCY", "ELECTIVE", "URGENT"]
CARE_UNITS = ["MICU", "SICU", "CCU", "CVICU", "NICU", "TSICU"]


def _step1_drop_high_missing(df: pd.DataFrame, threshold: float = 0.30) -> pd.DataFrame:
    """Remove rows with > 30% missing values."""
    n_cols = len(df.columns)
    missing_frac = df.isnull().sum(axis=1) / n_cols
    mask = missing_frac <= threshold
    dropped = (~mask).sum()
    logger.info("step1_drop_high_missing", dropped=int(dropped), remaining=int(mask.sum()))
    return df[mask].copy()


def _step2_median_imputation(
    df: pd.DataFrame,
    numeric_cols: list,
    population_medians: dict = None,
    fit: bool = True,
) -> tuple:
    """
    Per-patient median imputation.
    If patient has >= 3 readings, use their median; else use population median.
    Population median is fit on training data only.
    """
    if fit:
        population_medians = {}
        for col in numeric_cols:
            if col in df.columns:
                population_medians[col] = float(df[col].median())

    id_col = "HADM_ID" if "HADM_ID" in df.columns else "hadm_id"

    for col in numeric_cols:
        if col not in df.columns:
            continue
        # Per-patient median
        patient_medians = df.groupby(id_col)[col].transform(
            lambda x: x.median() if x.count() >= 3 else np.nan
        )
        # Fill with patient median first, then population median
        df[col] = df[col].fillna(patient_medians)
        if population_medians and col in population_medians:
            df[col] = df[col].fillna(population_medians[col])

    logger.info("step2_median_imputation", fit=fit, cols=len(numeric_cols))
    return df, population_medians


def _step3_iqr_clipping(
    df: pd.DataFrame,
    numeric_cols: list,
    iqr_bounds: dict = None,
    fit: bool = True,
) -> tuple:
    """
    IQR outlier clipping.
    Fit bounds on training set ONLY; apply to val/test.
    """
    if fit:
        iqr_bounds = {}
        for col in numeric_cols:
            if col not in df.columns:
                continue
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            iqr_bounds[col] = {
                "lower": float(q1 - 1.5 * iqr),
                "upper": float(q3 + 1.5 * iqr),
            }

    for col in numeric_cols:
        if col not in df.columns or col not in iqr_bounds:
            continue
        bounds = iqr_bounds[col]
        df[col] = df[col].clip(lower=bounds["lower"], upper=bounds["upper"])

    logger.info("step3_iqr_clipping", fit=fit, cols=len(numeric_cols))
    return df, iqr_bounds


def _step4_scale(
    df: pd.DataFrame,
    numeric_cols: list,
    scaler: StandardScaler = None,
    fit: bool = True,
) -> tuple:
    """
    StandardScaler normalization.
    Fit on training set ONLY. Save scaler as artifact.
    """
    cols_present = [c for c in numeric_cols if c in df.columns]
    if fit:
        scaler = StandardScaler()
        df[cols_present] = scaler.fit_transform(df[cols_present])
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, ARTIFACTS_DIR / "scaler.joblib")
        logger.info("step4_scaler_saved", path=str(ARTIFACTS_DIR / "scaler.joblib"))
    else:
        df[cols_present] = scaler.transform(df[cols_present])

    logger.info("step4_scale", fit=fit, cols=len(cols_present))
    return df, scaler


def _step5_one_hot_encode(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode admission_type and care_unit."""
    # admission_type
    if "ADMISSION_TYPE" in df.columns:
        for atype in ADMISSION_TYPES:
            df[f"admission_type_{atype}"] = (
                df["ADMISSION_TYPE"].str.upper() == atype
            ).astype(int)
        df.drop(columns=["ADMISSION_TYPE"], inplace=True, errors="ignore")

    # care_unit
    unit_col = None
    for candidate in ["FIRST_CAREUNIT", "CURR_CAREUNIT", "care_unit"]:
        if candidate in df.columns:
            unit_col = candidate
            break

    if unit_col:
        for unit in CARE_UNITS:
            df[f"care_unit_{unit}"] = (
                df[unit_col].str.upper() == unit
            ).astype(int)
        # "other" category
        known = df[unit_col].str.upper().isin(CARE_UNITS)
        df["care_unit_other"] = (~known).astype(int)
        df.drop(columns=[unit_col], inplace=True, errors="ignore")
    else:
        # Fill with zeros
        for unit in CARE_UNITS + ["other"]:
            if f"care_unit_{unit}" not in df.columns:
                df[f"care_unit_{unit}"] = 0

    logger.info("step5_one_hot_encode")
    return df


def _step6_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract time-based features."""
    time_col = "CHARTTIME" if "CHARTTIME" in df.columns else "charttime"
    admit_col = "ADMITTIME" if "ADMITTIME" in df.columns else "admittime"

    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")

    if admit_col in df.columns:
        df[admit_col] = pd.to_datetime(df[admit_col], errors="coerce")
        if time_col in df.columns:
            df["hours_since_admission"] = (
                (df[time_col] - df[admit_col]).dt.total_seconds() / 3600
            ).clip(lower=0)
        else:
            df["hours_since_admission"] = 0.0
    else:
        df["hours_since_admission"] = 0.0

    # Time since last vital / lab (placeholder — populated during feature assembly)
    if "time_since_last_vital_hours" not in df.columns:
        df["time_since_last_vital_hours"] = 0.0
    if "time_since_last_lab_hours" not in df.columns:
        df["time_since_last_lab_hours"] = 0.0

    # Night shift flag
    if time_col in df.columns and pd.api.types.is_datetime64_any_dtype(df[time_col]):
        hour = df[time_col].dt.hour
        df["is_night_shift"] = ((hour >= 20) | (hour < 6)).astype(int)
    else:
        df["is_night_shift"] = 0

    logger.info("step6_time_features")
    return df


def split_by_admission(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    random_state: int = 42,
) -> tuple:
    """
    Split DataFrame by HADM_ID (hospital admission).
    No patient leakage across splits.
    """
    id_col = "HADM_ID" if "HADM_ID" in df.columns else "hadm_id"
    hadm_ids = df[id_col].unique()
    np.random.seed(random_state)
    np.random.shuffle(hadm_ids)

    n = len(hadm_ids)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)

    train_ids = hadm_ids[:n_train]
    val_ids = hadm_ids[n_train : n_train + n_val]
    test_ids = hadm_ids[n_train + n_val :]

    train_df = df[df[id_col].isin(train_ids)].copy()
    val_df = df[df[id_col].isin(val_ids)].copy()
    test_df = df[df[id_col].isin(test_ids)].copy()

    logger.info(
        "split_by_admission",
        train=len(train_df), val=len(val_df), test=len(test_df),
        train_admissions=len(train_ids),
        val_admissions=len(val_ids),
        test_admissions=len(test_ids),
    )
    return train_df, val_df, test_df


def run_cleaning_pipeline(
    df: pd.DataFrame,
    numeric_cols: list,
    fit: bool = True,
    fitted_params: dict = None,
) -> tuple:
    """
    Run the full sequential cleaning pipeline.

    Parameters
    ----------
    df : pd.DataFrame
    numeric_cols : list of str — numeric columns to clean
    fit : bool — True for training set, False for val/test
    fitted_params : dict — previously fitted parameters (for val/test)

    Returns
    -------
    (cleaned_df, fitted_params_dict)
    """
    if fitted_params is None:
        fitted_params = {}

    # Step 1: Drop high-missing rows
    df = _step1_drop_high_missing(df)

    # Step 2: Median imputation
    df, pop_medians = _step2_median_imputation(
        df, numeric_cols,
        population_medians=fitted_params.get("population_medians"),
        fit=fit,
    )
    if fit:
        fitted_params["population_medians"] = pop_medians

    # Step 3: IQR clipping
    df, iqr_bounds = _step3_iqr_clipping(
        df, numeric_cols,
        iqr_bounds=fitted_params.get("iqr_bounds"),
        fit=fit,
    )
    if fit:
        fitted_params["iqr_bounds"] = iqr_bounds

    # Step 4: StandardScaler
    df, scaler = _step4_scale(
        df, numeric_cols,
        scaler=fitted_params.get("scaler"),
        fit=fit,
    )
    if fit:
        fitted_params["scaler"] = scaler

    # Step 5: One-hot encode
    df = _step5_one_hot_encode(df)

    # Step 6: Time features
    df = _step6_time_features(df)

    logger.info("cleaning_pipeline_complete", shape=df.shape, fit=fit)
    return df, fitted_params

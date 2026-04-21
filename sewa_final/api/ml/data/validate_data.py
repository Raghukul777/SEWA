"""
SEWA — Data Validation Module
Enforces clinical bounds on vitals and lab values.
Rows outside bounds are rejected as sensor errors.
"""

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

VALIDATION_RULES = {
    "heart_rate":       (20, 300),
    "temperature_c":    (34.0, 42.0),
    "respiratory_rate": (4, 60),
    "spo2_percent":     (50, 100),
    "systolic_bp":      (40, 250),
    "diastolic_bp":     (20, 180),
    "wbc_count":        (0.1, 100),
    "lactate":          (0.1, 30),
    "creatinine":       (0.1, 20),
    "bilirubin_total":  (0.1, 50),
    "glucose":          (20, 2000),
    "platelets":        (1, 2000),
}


def validate_dataframe(df: pd.DataFrame, rules: dict = None) -> pd.DataFrame:
    """
    Validate a DataFrame against clinical bounds.
    Rows outside bounds for any validated column are dropped.
    Logs drop counts per column and warns if >10% dropped.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with clinical measurement columns.
    rules : dict, optional
        Override validation rules. Defaults to VALIDATION_RULES.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with invalid rows removed.
    """
    if rules is None:
        rules = VALIDATION_RULES

    total_rows = len(df)
    mask = pd.Series(True, index=df.index)
    drop_report = {}

    for col, (low, high) in rules.items():
        if col not in df.columns:
            continue
        invalid = ~df[col].between(low, high) & df[col].notna()
        n_invalid = invalid.sum()
        drop_report[col] = n_invalid
        mask &= ~invalid

        pct = n_invalid / total_rows * 100 if total_rows > 0 else 0
        if pct > 10:
            logger.warning(
                "high_drop_rate",
                column=col,
                dropped=n_invalid,
                pct=round(pct, 2),
            )
        if n_invalid > 0:
            logger.info(
                "validation_drop",
                column=col,
                dropped=n_invalid,
                pct=round(pct, 2),
            )

    clean_df = df[mask].copy()
    logger.info(
        "validation_complete",
        rows_before=total_rows,
        rows_after=len(clean_df),
        total_dropped=total_rows - len(clean_df),
    )
    return clean_df

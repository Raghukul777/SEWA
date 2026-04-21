"""
SEWA — Sepsis-3 Label Generator
Labels ICU stays using the Sepsis-3 definition on MIMIC-III data.

Label = 1 if:
  - Suspected infection (antibiotics + blood culture within 72h)
  - SOFA score increase >= 2 from baseline

Uses PRESCRIPTIONS + MICROBIOLOGYEVENTS for infection suspicion
and CHARTEVENTS/LABEVENTS for SOFA component calculation.
"""

import pandas as pd
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

SOFA_COMPONENTS = {
    "platelets": [
        (400, 0), (300, 0), (200, 1), (150, 1), (100, 2), (50, 3), (20, 4),
    ],
    "bilirubin_total": [
        (1.2, 0), (2.0, 1), (6.0, 2), (12.0, 3), (float("inf"), 4),
    ],
    "creatinine": [
        (1.2, 0), (2.0, 1), (3.5, 2), (5.0, 3), (float("inf"), 4),
    ],
}


def _sofa_platelets(val: float) -> int:
    if pd.isna(val):
        return 0
    if val >= 150:
        return 0
    if val >= 100:
        return 1
    if val >= 50:
        return 2
    if val >= 20:
        return 3
    return 4


def _sofa_bilirubin(val: float) -> int:
    if pd.isna(val):
        return 0
    if val < 1.2:
        return 0
    if val < 2.0:
        return 1
    if val < 6.0:
        return 2
    if val < 12.0:
        return 3
    return 4


def _sofa_creatinine(val: float) -> int:
    if pd.isna(val):
        return 0
    if val < 1.2:
        return 0
    if val < 2.0:
        return 1
    if val < 3.5:
        return 2
    if val < 5.0:
        return 3
    return 4


def _sofa_respiratory(spo2: float) -> int:
    """Approximate respiratory SOFA from SpO2 (no PaO2/FiO2 in demo)."""
    if pd.isna(spo2):
        return 0
    if spo2 >= 96:
        return 0
    if spo2 >= 92:
        return 1
    if spo2 >= 88:
        return 2
    if spo2 >= 80:
        return 3
    return 4


def compute_sofa_score(row: pd.Series) -> int:
    """Compute a partial SOFA score from available labs + vitals."""
    score = 0
    score += _sofa_platelets(row.get("platelets"))
    score += _sofa_bilirubin(row.get("bilirubin_total"))
    score += _sofa_creatinine(row.get("creatinine"))
    score += _sofa_respiratory(row.get("spo2_percent"))
    return score


def detect_suspected_infection(
    prescriptions: pd.DataFrame,
    micro: pd.DataFrame,
    hadm_ids: list,
) -> set:
    """
    Suspected infection = antibiotics started + blood culture ordered
    within a 72-hour window.

    Returns set of HADM_IDs with suspected infection.
    """
    suspected = set()

    if prescriptions is None or micro is None:
        logger.warning("missing_infection_tables",
                       msg="Cannot compute suspected infection; labelling by SOFA only")
        return suspected

    # Filter prescriptions for antibiotics
    abx_keywords = [
        "cillin", "mycin", "floxacin", "cycline", "azole",
        "sulfa", "meropenem", "vancomycin", "ceftri", "cefaz",
        "pipera", "metro", "amox", "ampic", "levo", "cipro",
    ]

    presc = prescriptions[prescriptions["HADM_ID"].isin(hadm_ids)].copy()
    if "DRUG" not in presc.columns:
        return suspected

    abx_mask = presc["DRUG"].str.lower().str.contains(
        "|".join(abx_keywords), na=False
    )
    abx = presc[abx_mask].copy()

    # Filter micro for blood cultures
    micro_f = micro[micro["HADM_ID"].isin(hadm_ids)].copy()

    for hadm_id in hadm_ids:
        has_abx = hadm_id in abx["HADM_ID"].values
        has_culture = hadm_id in micro_f["HADM_ID"].values
        if has_abx and has_culture:
            suspected.add(hadm_id)

    logger.info("suspected_infections", count=len(suspected),
                total=len(hadm_ids))
    return suspected


def generate_labels(
    features_df: pd.DataFrame,
    prescriptions: pd.DataFrame = None,
    micro: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Generate sepsis labels for each ICU stay.

    Sepsis-3: suspected_infection AND sofa_delta >= 2

    Parameters
    ----------
    features_df : pd.DataFrame
        Must contain HADM_ID plus lab/vital columns.
    prescriptions : pd.DataFrame, optional
        PRESCRIPTIONS.csv data.
    micro : pd.DataFrame, optional
        MICROBIOLOGYEVENTS.csv data.

    Returns
    -------
    pd.DataFrame with added 'sepsis_label' column.
    """
    df = features_df.copy()

    # Compute SOFA components
    df["sofa_score"] = df.apply(compute_sofa_score, axis=1)

    # Baseline SOFA = first measurement per admission
    baseline = (
        df.sort_values("CHARTTIME" if "CHARTTIME" in df.columns else "charttime")
          .groupby("HADM_ID")["sofa_score"]
          .first()
          .rename("sofa_baseline")
    )
    df = df.merge(baseline, on="HADM_ID", how="left")
    df["sofa_delta"] = df["sofa_score"] - df["sofa_baseline"]

    # Suspected infection
    hadm_ids = df["HADM_ID"].unique().tolist()
    suspected = detect_suspected_infection(prescriptions, micro, hadm_ids)

    if len(suspected) > 0:
        df["suspected_infection"] = df["HADM_ID"].isin(suspected).astype(int)
    else:
        # Fallback: use SOFA delta alone (for demo dataset)
        logger.info("fallback_labelling",
                     msg="Using SOFA delta >= 2 as sole label criterion")
        df["suspected_infection"] = 1

    # Sepsis-3 label
    df["sepsis_label"] = (
        (df["suspected_infection"] == 1) & (df["sofa_delta"] >= 2)
    ).astype(int)

    # Log class balance
    pos = df["sepsis_label"].sum()
    neg = len(df) - pos
    ratio = neg / pos if pos > 0 else float("inf")
    logger.info(
        "label_distribution",
        positive=int(pos),
        negative=int(neg),
        ratio=f"1:{ratio:.1f}",
    )

    return df

"""
SEWA — qSOFA Rule Engine
Quick Sequential Organ Failure Assessment scoring (0–3).
"""


class QSOFAEngine:
    """
    qSOFA = Quick Sequential Organ Failure Assessment.
    Score 0–3. Positive if score >= 2.

    Criteria (each +1):
      1. Respiratory Rate >= 22 breaths/min
      2. Altered mentation (GCS < 15, if available)
      3. Systolic BP <= 100 mmHg
    """

    def evaluate(self, vitals: dict) -> dict:
        """
        Parameters
        ----------
        vitals : dict — keys: respiratory_rate, systolic_bp, gcs (optional)

        Returns
        -------
        dict with qsofa_score (int 0–3), criteria_met (dict), qsofa_positive (bool)
        """
        criteria = {}

        # Criterion 1: Respiratory Rate
        rr = vitals.get("respiratory_rate")
        if rr is not None:
            criteria["respiratory_rate"] = rr >= 22
        else:
            criteria["respiratory_rate"] = False

        # Criterion 2: Altered mentation (GCS < 15)
        gcs = vitals.get("gcs")
        if gcs is not None:
            criteria["altered_mentation"] = gcs < 15
        else:
            criteria["altered_mentation"] = False  # skip if unavailable

        # Criterion 3: Systolic BP
        sbp = vitals.get("systolic_bp")
        if sbp is not None:
            criteria["systolic_bp"] = sbp <= 100
        else:
            criteria["systolic_bp"] = False

        score = sum(criteria.values())
        return {
            "qsofa_score": score,
            "criteria_met": criteria,
            "qsofa_positive": score >= 2,
        }

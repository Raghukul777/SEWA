"""
SEWA — SIRS Rule Engine
Systemic Inflammatory Response Syndrome scoring (0–4).
"""


class SIRSEngine:
    """
    SIRS = Systemic Inflammatory Response Syndrome.
    Score 0–4. Positive if score >= 2.

    Criteria (each +1):
      1. Temperature > 38.3°C OR < 36.0°C
      2. Heart Rate > 90 bpm
      3. Respiratory Rate > 20 breaths/min
      4. WBC > 12.0 x10^9/L OR < 4.0 x10^9/L
    """

    def evaluate(self, vitals: dict, labs: dict) -> dict:
        """
        Parameters
        ----------
        vitals : dict  — keys: temperature_c, heart_rate, respiratory_rate
        labs   : dict  — keys: wbc_count

        Returns
        -------
        dict with sirs_score (int 0–4), criteria_met (dict), sirs_positive (bool)
        """
        criteria = {}

        # Criterion 1: Temperature
        temp = vitals.get("temperature_c")
        if temp is not None:
            criteria["temperature"] = temp > 38.3 or temp < 36.0
        else:
            criteria["temperature"] = False

        # Criterion 2: Heart Rate
        hr = vitals.get("heart_rate")
        if hr is not None:
            criteria["heart_rate"] = hr > 90
        else:
            criteria["heart_rate"] = False

        # Criterion 3: Respiratory Rate
        rr = vitals.get("respiratory_rate")
        if rr is not None:
            criteria["respiratory_rate"] = rr > 20
        else:
            criteria["respiratory_rate"] = False

        # Criterion 4: WBC
        wbc = labs.get("wbc_count")
        if wbc is not None:
            criteria["wbc"] = wbc > 12.0 or wbc < 4.0
        else:
            criteria["wbc"] = False

        score = sum(criteria.values())
        return {
            "sirs_score": score,
            "criteria_met": criteria,
            "sirs_positive": score >= 2,
        }

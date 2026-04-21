"""
SEWA — Model Monitoring Module
Weekly drift detection, performance tracking, and alert management.
"""

import numpy as np
import pandas as pd
import joblib
import json
from datetime import datetime
from pathlib import Path
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
import structlog

logger = structlog.get_logger(__name__)

MONITORING_THRESHOLDS = {
    "auroc_drop_alert":     0.05,
    "feature_mean_shift":   2.0,    # std devs
    "alert_rate_change":    0.30,
    "fallback_rate_target": 0.0,
}


class ModelMonitor:
    """
    Tracks model performance and data drift over time.
    Call run_weekly_check() on a scheduled basis.
    """

    def __init__(
        self,
        baseline_path: str = "app/ml/artifacts/training_baseline.json",
        feature_names_path: str = "app/ml/artifacts/feature_names.joblib",
    ):
        self.baseline_path = Path(baseline_path)
        self.feature_names_path = Path(feature_names_path)
        self.baseline = self._load_baseline()
        self.feature_names = self._load_feature_names()

    def _load_baseline(self) -> dict:
        if self.baseline_path.exists():
            with open(self.baseline_path) as f:
                return json.load(f)
        return {}

    def _load_feature_names(self) -> list:
        if self.feature_names_path.exists():
            return joblib.load(self.feature_names_path)
        return []

    @staticmethod
    def save_training_baseline(
        X_train: np.ndarray,
        feature_names: list,
        train_auroc: float,
        train_auprc: float,
        save_path: str = "app/ml/artifacts/training_baseline.json",
    ):
        """Save training-time statistics as the baseline for drift detection."""
        baseline = {
            "timestamp": datetime.utcnow().isoformat(),
            "train_auroc": train_auroc,
            "train_auprc": train_auprc,
            "feature_stats": {},
        }
        for i, name in enumerate(feature_names):
            col = X_train[:, i]
            baseline["feature_stats"][name] = {
                "mean": float(np.nanmean(col)),
                "std": float(np.nanstd(col)),
            }
        with open(save_path, "w") as f:
            json.dump(baseline, f, indent=2)
        logger.info("training_baseline_saved", path=save_path)

    def check_performance(
        self, y_true: np.ndarray, y_prob: np.ndarray
    ) -> dict:
        """Compute current performance metrics and compare to baseline."""
        auroc = roc_auc_score(y_true, y_prob)
        auprc = average_precision_score(y_true, y_prob)
        brier = brier_score_loss(y_true, y_prob)

        alerts = []
        if self.baseline:
            base_auroc = self.baseline.get("train_auroc", 0)
            if base_auroc - auroc > MONITORING_THRESHOLDS["auroc_drop_alert"]:
                alerts.append({
                    "type": "AUROC_DROP",
                    "severity": "HIGH",
                    "message": f"AUROC dropped from {base_auroc:.4f} to {auroc:.4f}",
                })

        result = {
            "auroc": auroc,
            "auprc": auprc,
            "brier_score": brier,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info("performance_check", **{k: v for k, v in result.items() if k != "alerts"})
        for a in alerts:
            logger.warning("performance_alert", **a)
        return result

    def check_feature_drift(self, X_current: np.ndarray) -> dict:
        """
        Compare current feature distributions against training baseline.
        Alert if mean shifts by >2 standard deviations.
        """
        if not self.baseline or "feature_stats" not in self.baseline:
            return {"status": "no_baseline", "alerts": []}

        alerts = []
        stats = self.baseline["feature_stats"]

        for i, name in enumerate(self.feature_names):
            if name not in stats:
                continue
            base_mean = stats[name]["mean"]
            base_std = stats[name]["std"]
            if base_std == 0:
                continue

            current_mean = float(np.nanmean(X_current[:, i]))
            shift = abs(current_mean - base_mean) / base_std

            if shift > MONITORING_THRESHOLDS["feature_mean_shift"]:
                alerts.append({
                    "type": "FEATURE_DRIFT",
                    "feature": name,
                    "severity": "MEDIUM",
                    "shift_std": round(shift, 2),
                    "base_mean": round(base_mean, 4),
                    "current_mean": round(current_mean, 4),
                })

        for a in alerts:
            logger.warning("feature_drift_alert", **a)
        return {"alerts": alerts, "timestamp": datetime.utcnow().isoformat()}

    def check_alert_rate(
        self, current_alerts: int, previous_alerts: int
    ) -> dict:
        """Check if weekly alert rate changed significantly."""
        if previous_alerts == 0:
            change = 1.0 if current_alerts > 0 else 0.0
        else:
            change = abs(current_alerts - previous_alerts) / previous_alerts

        alerts = []
        if change > MONITORING_THRESHOLDS["alert_rate_change"]:
            alerts.append({
                "type": "ALERT_RATE_CHANGE",
                "severity": "MEDIUM",
                "change_pct": round(change * 100, 1),
            })

        return {"change_pct": round(change * 100, 1), "alerts": alerts}

    def run_weekly_check(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        X_current: np.ndarray,
        current_week_alerts: int = 0,
        previous_week_alerts: int = 0,
        fallback_count: int = 0,
    ) -> dict:
        """Run all weekly monitoring checks."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "performance": self.check_performance(y_true, y_prob),
            "drift": self.check_feature_drift(X_current),
            "alert_rate": self.check_alert_rate(
                current_week_alerts, previous_week_alerts
            ),
            "fallback_count": fallback_count,
        }

        if fallback_count > MONITORING_THRESHOLDS["fallback_rate_target"]:
            logger.error(
                "ml_fallback_detected",
                count=fallback_count,
                msg="XGBoost fallbacks detected — investigate immediately",
            )

        all_alerts = (
            report["performance"]["alerts"]
            + report["drift"]["alerts"]
            + report["alert_rate"]["alerts"]
        )
        report["total_alerts"] = len(all_alerts)
        logger.info("weekly_report_complete", total_alerts=len(all_alerts))
        return report

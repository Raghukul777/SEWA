"""
SEWA — SHAP Explainability Module
Per-prediction explanations using TreeExplainer.
"""

import numpy as np
import shap
import joblib
import structlog

logger = structlog.get_logger(__name__)


def create_and_save_explainer(model, save_path: str = "app/ml/artifacts/shap_explainer.joblib"):
    """
    Create a SHAP TreeExplainer from a trained XGBoost model and save it.
    Called once after training.
    """
    explainer = shap.TreeExplainer(model)
    joblib.dump(explainer, save_path)
    logger.info("shap_explainer_saved", path=save_path)
    return explainer


def load_explainer(path: str = "app/ml/artifacts/shap_explainer.joblib"):
    """Load a saved SHAP explainer."""
    return joblib.load(path)


def explain_prediction(
    explainer,
    X_single_row: np.ndarray,
    feature_names: list,
    top_n: int = 10,
) -> dict:
    """
    Generate top-N SHAP feature explanations for a single prediction.

    Positive SHAP = increases sepsis risk.
    Negative SHAP = protective / reduces risk.

    Parameters
    ----------
    explainer : shap.TreeExplainer
    X_single_row : np.ndarray, shape (1, n_features)
    feature_names : list of str
    top_n : int

    Returns
    -------
    dict : {feature_name: shap_value} sorted by |shap_value| descending
    """
    shap_values = explainer.shap_values(X_single_row)

    # Handle different shap output formats
    if isinstance(shap_values, list):
        # Binary classification: take positive class
        vals = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
    elif isinstance(shap_values, np.ndarray):
        vals = shap_values[0] if shap_values.ndim > 1 else shap_values
    else:
        vals = np.array(shap_values)

    explanation = dict(zip(feature_names, vals.tolist()))
    top = dict(
        sorted(explanation.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]
    )
    return top

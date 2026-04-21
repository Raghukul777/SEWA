"""
SEWA — Hyperparameter Search using Optuna
Searches over XGBoost hyperparameters using 3-fold CV.
"""

import optuna
import xgboost as xgb
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import structlog

logger = structlog.get_logger(__name__)

CONFIGS_DIR = Path("app/ml/configs")


def objective(trial, X, y):
    """Optuna objective: maximize AUROC via 3-fold CV."""
    params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "tree_method": "hist",
        "random_state": 42,
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.3, log=True),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 3, 20),
        "gamma": trial.suggest_float("gamma", 0.0, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 2.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 3.0),
        "n_estimators": 500,
        "early_stopping_rounds": 50,
    }

    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    scores = []

    for train_idx, val_idx in skf.split(X, y):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBClassifier(**params, use_label_encoder=False)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        preds = model.predict_proba(X_val)[:, 1]
        scores.append(roc_auc_score(y_val, preds))

    return np.mean(scores)


def run_hpo(X: np.ndarray, y: np.ndarray, n_trials: int = 100) -> dict:
    """
    Run Optuna hyperparameter optimization.
    Saves best params to configs/best_params.json.
    Returns best params dict.
    """
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, X, y), n_trials=n_trials,
                   show_progress_bar=True)

    best = study.best_params
    best["objective"] = "binary:logistic"
    best["eval_metric"] = "auc"
    best["tree_method"] = "hist"
    best["random_state"] = 42
    best["n_estimators"] = 500
    best["early_stopping_rounds"] = 50

    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIGS_DIR / "best_params.json", "w") as f:
        json.dump(best, f, indent=2)

    logger.info("hpo_complete", best_auroc=study.best_value, best_params=best)
    return best

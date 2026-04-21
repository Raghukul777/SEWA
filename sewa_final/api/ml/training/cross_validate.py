"""
SEWA — 5-Fold Cross-Validation with OOF Predictions
"""

import numpy as np
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
import structlog

logger = structlog.get_logger(__name__)


def run_cross_validation(
    X: np.ndarray,
    y: np.ndarray,
    params: dict,
    n_splits: int = 5,
    random_state: int = 42,
) -> dict:
    """
    Run 5-fold stratified CV with out-of-fold predictions.

    Returns
    -------
    dict with keys:
        oof_preds, fold_aurocs, fold_auprcs, fold_briers,
        mean_auroc, std_auroc, mean_auprc, mean_brier
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    oof_preds = np.zeros(len(y))
    fold_aurocs = []
    fold_auprcs = []
    fold_briers = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBClassifier(**params, use_label_encoder=False)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        preds = model.predict_proba(X_val)[:, 1]
        oof_preds[val_idx] = preds

        auroc = roc_auc_score(y_val, preds)
        auprc = average_precision_score(y_val, preds)
        brier = brier_score_loss(y_val, preds)

        fold_aurocs.append(auroc)
        fold_auprcs.append(auprc)
        fold_briers.append(brier)

        logger.info(
            f"fold_{fold+1}",
            auroc=round(auroc, 4),
            auprc=round(auprc, 4),
            brier=round(brier, 4),
        )

    mean_auroc = np.mean(fold_aurocs)
    std_auroc = np.std(fold_aurocs)
    mean_auprc = np.mean(fold_auprcs)
    mean_brier = np.mean(fold_briers)

    logger.info(
        "cv_summary",
        mean_auroc=round(mean_auroc, 4),
        std_auroc=round(std_auroc, 4),
        mean_auprc=round(mean_auprc, 4),
        mean_brier=round(mean_brier, 4),
    )

    return {
        "oof_preds": oof_preds,
        "fold_aurocs": fold_aurocs,
        "fold_auprcs": fold_auprcs,
        "fold_briers": fold_briers,
        "mean_auroc": mean_auroc,
        "std_auroc": std_auroc,
        "mean_auprc": mean_auprc,
        "mean_brier": mean_brier,
    }

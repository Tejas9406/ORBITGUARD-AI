"""Anomaly detection evaluation metrics module for OrbitGuard AI.

Provides rigorous performance evaluation for binary predictions (Accuracy,
Precision, Recall, Specificity, F1-Score, Confusion Matrix) and continuous anomaly
scores (ROC-AUC, PR-AUC), with safe handling for zero-division and single-class edge cases.
"""

from typing import Any, Dict, Optional, Sequence, Union
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


def _sanitize_binary_array(arr: Union[np.ndarray, pd.Series, Sequence], name: str) -> np.ndarray:
    """Validates and converts input into a 1D binary numpy array of integers {0, 1}."""
    if arr is None:
        raise ValueError(f"{name} cannot be None.")
    np_arr = np.asarray(arr)
    if np_arr.size == 0:
        raise ValueError(f"{name} cannot be empty.")
    if np_arr.ndim != 1:
        np_arr = np_arr.ravel()

    # Check finite
    if not np.isfinite(np_arr).all():
        raise ValueError(f"{name} contains non-finite (NaN or Inf) values.")

    unique_vals = set(np.unique(np_arr))
    if not unique_vals.issubset({0, 1}):
        raise ValueError(f"{name} must contain only binary values (0 or 1), got {unique_vals}.")

    return np_arr.astype(int)


def compute_confusion_matrix(
    y_true: Union[np.ndarray, pd.Series, Sequence],
    y_pred: Union[np.ndarray, pd.Series, Sequence],
) -> Dict[str, int]:
    """Computes binary confusion matrix counts for anomaly detection.

    Convention:
    - 1 = Anomaly (Positive)
    - 0 = Nominal (Negative)

    Args:
        y_true: Ground truth binary labels.
        y_pred: Predicted binary labels.

    Returns:
        Dict[str, int]: Counts of true positives ('tp'), false positives ('fp'),
            true negatives ('tn'), and false negatives ('fn').

    Raises:
        ValueError: If lengths mismatch, inputs are empty, or non-binary values are present.
    """
    yt = _sanitize_binary_array(y_true, "y_true")
    yp = _sanitize_binary_array(y_pred, "y_pred")

    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(y_pred)={len(yp)}.")

    tp = int(np.sum((yt == 1) & (yp == 1)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fn = int(np.sum((yt == 1) & (yp == 0)))

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "total": len(yt),
    }


def compute_classification_metrics(
    y_true: Union[np.ndarray, pd.Series, Sequence],
    y_pred: Union[np.ndarray, pd.Series, Sequence],
    zero_division: float = 0.0,
) -> Dict[str, float]:
    """Computes classification metrics for binary anomaly predictions.

    Handles zero-division gracefully:
    - Precision is undefined when (tp + fp) == 0; returns `zero_division`.
    - Recall is undefined when (tp + fn) == 0; returns `zero_division`.
    - Specificity is undefined when (tn + fp) == 0; returns `zero_division`.
    - F1-Score is undefined when (precision + recall) == 0; returns `zero_division`.

    Args:
        y_true: Ground truth binary labels (1=anomaly, 0=nominal).
        y_pred: Predicted binary labels (1=anomaly, 0=nominal).
        zero_division: Value returned when a metric's denominator is zero. Defaults to 0.0.

    Returns:
        Dict[str, float]: Accuracy, precision, recall, specificity, f1_score, and counts.
    """
    cm = compute_confusion_matrix(y_true, y_pred)
    tp, fp, tn, fn, total = cm["tp"], cm["fp"], cm["tn"], cm["fn"], cm["total"]

    accuracy = (tp + tn) / total if total > 0 else zero_division
    precision = tp / (tp + fp) if (tp + fp) > 0 else zero_division
    recall = tp / (tp + fn) if (tp + fn) > 0 else zero_division
    specificity = tn / (tn + fp) if (tn + fp) > 0 else zero_division

    f1 = (
        (2.0 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else zero_division
    )

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "specificity": float(specificity),
        "f1_score": float(f1),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "total": total,
    }


def compute_ranking_metrics(
    y_true: Union[np.ndarray, pd.Series, Sequence],
    scores: Union[np.ndarray, pd.Series, Sequence],
) -> Dict[str, Optional[float]]:
    """Computes threshold-independent ranking metrics: ROC-AUC and PR-AUC.

    Under the project convention, higher continuous scores indicate higher anomaly likelihood.

    Edge Cases:
    - If `y_true` contains only one class (all 0s or all 1s), ROC-AUC and PR-AUC
      are mathematically undefined and `None` is returned.
    - If all anomaly scores are identical (constant prediction), metrics are evaluated
      normally (ROC-AUC will be 0.5).

    Args:
        y_true: Ground truth binary labels.
        scores: Continuous anomaly scores (higher = more anomalous).

    Returns:
        Dict[str, Optional[float]]: 'roc_auc' and 'pr_auc' (Average Precision).
    """
    yt = _sanitize_binary_array(y_true, "y_true")
    if scores is None:
        raise ValueError("scores cannot be None.")
    sc = np.asarray(scores, dtype=float)
    if sc.size == 0:
        raise ValueError("scores cannot be empty.")
    if sc.ndim != 1:
        sc = sc.ravel()
    if len(yt) != len(sc):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(scores)={len(sc)}.")
    if not np.isfinite(sc).all():
        raise ValueError("scores contains non-finite (NaN or Inf) values.")

    # Check for single-class ground truth
    unique_classes = np.unique(yt)
    if len(unique_classes) < 2:
        return {
            "roc_auc": None,
            "pr_auc": None,
        }

    try:
        roc_auc = float(roc_auc_score(yt, sc))
    except ValueError:
        roc_auc = None

    try:
        pr_auc = float(average_precision_score(yt, sc))
    except ValueError:
        pr_auc = None

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
    }


def compute_per_anomaly_type_recall(
    y_true: Union[np.ndarray, pd.Series, Sequence],
    y_pred: Union[np.ndarray, pd.Series, Sequence],
    anomaly_types: Union[np.ndarray, pd.Series, Sequence],
    zero_division: float = 0.0,
) -> Dict[str, Dict[str, Union[float, int]]]:
    """Computes detection recall and test support count for each distinct non-nominal anomaly category.

    Args:
        y_true: Ground truth binary labels (1=anomaly, 0=nominal).
        y_pred: Predicted binary labels (1=anomaly, 0=nominal).
        anomaly_types: Sequence of anomaly type strings (e.g. 'voltage_drop', 'gyro_glitch').
        zero_division: Value returned when a category has zero actual occurrences. Defaults to 0.0.

    Returns:
        Dict[str, Dict[str, Union[float, int]]]: Mapping from anomaly type to a dictionary containing:
            - 'recall' (float): Detection recall (0.0 to 1.0).
            - 'support' (int): Total number of ground-truth occurrences of this anomaly type.
    """
    yt = _sanitize_binary_array(y_true, "y_true")
    yp = _sanitize_binary_array(y_pred, "y_pred")
    at = np.asarray(anomaly_types)

    if len(yt) != len(at):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(anomaly_types)={len(at)}.")

    categories = [cat for cat in np.unique(at) if str(cat).lower() != "nominal"]
    results: Dict[str, Dict[str, Union[float, int]]] = {}

    for cat in sorted(categories):
        mask = (at == cat)
        total_in_cat = int(np.sum(mask))
        if total_in_cat == 0:
            results[str(cat)] = {"recall": zero_division, "support": 0}
        else:
            detected_in_cat = int(np.sum(yp[mask] == 1))
            results[str(cat)] = {
                "recall": float(detected_in_cat / total_in_cat),
                "support": total_in_cat,
            }

    return results


def evaluate_predictions(
    y_true: Union[np.ndarray, pd.Series, Sequence],
    y_pred: Union[np.ndarray, pd.Series, Sequence],
    scores: Optional[Union[np.ndarray, pd.Series, Sequence]] = None,
    anomaly_types: Optional[Union[np.ndarray, pd.Series, Sequence]] = None,
    zero_division: float = 0.0,
) -> Dict[str, Any]:
    """Comprehensive evaluation combining classification, ranking, and per-type metrics.

    Args:
        y_true: Ground truth binary labels.
        y_pred: Predicted binary labels.
        scores: Optional continuous anomaly scores.
        anomaly_types: Optional categorical anomaly labels for category breakdown.
        zero_division: Value returned for undefined ratios.

    Returns:
        Dict[str, Any]: Consolidated metrics dictionary.
    """
    metrics = compute_classification_metrics(y_true, y_pred, zero_division=zero_division)

    if scores is not None:
        ranking = compute_ranking_metrics(y_true, scores)
        metrics.update(ranking)
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None

    if anomaly_types is not None:
        type_recalls = compute_per_anomaly_type_recall(
            y_true, y_pred, anomaly_types, zero_division=zero_division
        )
        metrics["per_type_recall"] = type_recalls
    else:
        metrics["per_type_recall"] = {}

    return metrics

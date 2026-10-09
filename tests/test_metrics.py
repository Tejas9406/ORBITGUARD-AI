"""Unit tests for evaluation metrics and fair benchmarking."""

import numpy as np
import pytest

from src.evaluation.benchmark import run_benchmark
from src.evaluation.metrics import (
    compute_classification_metrics,
    compute_confusion_matrix,
    compute_per_anomaly_type_recall,
    compute_ranking_metrics,
    evaluate_predictions,
)


def test_perfect_predictions():
    """Verify metrics return 1.0 across all indicators for perfect predictions."""
    y_true = np.array([1, 0, 1, 0, 1])
    y_pred = np.array([1, 0, 1, 0, 1])
    metrics = compute_classification_metrics(y_true, y_pred)

    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["specificity"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["tp"] == 3
    assert metrics["tn"] == 2
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0


def test_completely_inverted_predictions():
    """Verify metrics return 0.0 for completely inverted predictions."""
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.array([0, 1, 0, 1])
    metrics = compute_classification_metrics(y_true, y_pred)

    assert metrics["accuracy"] == 0.0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["specificity"] == 0.0
    assert metrics["f1_score"] == 0.0
    assert metrics["tp"] == 0
    assert metrics["tn"] == 0
    assert metrics["fp"] == 2
    assert metrics["fn"] == 2


def test_confusion_matrix_explicit_counts():
    """Verify exact count allocation in confusion matrix."""
    # 2 TP (idx 0, 1), 1 FP (idx 2), 2 TN (idx 3, 4), 1 FN (idx 5)
    y_true = np.array([1, 1, 0, 0, 0, 1])
    y_pred = np.array([1, 1, 1, 0, 0, 0])
    cm = compute_confusion_matrix(y_true, y_pred)

    assert cm["tp"] == 2
    assert cm["fp"] == 1
    assert cm["tn"] == 2
    assert cm["fn"] == 1
    assert cm["total"] == 6


def test_zero_division_behavior():
    """Verify zero-division handling when positive predictions or actual positives are zero."""
    # All negatives, predicted all negatives
    y_true = np.array([0, 0, 0, 0])
    y_pred = np.array([0, 0, 0, 0])

    # Default zero_division=0.0
    metrics_default = compute_classification_metrics(y_true, y_pred, zero_division=0.0)
    assert metrics_default["precision"] == 0.0
    assert metrics_default["recall"] == 0.0
    assert metrics_default["f1_score"] == 0.0
    assert metrics_default["specificity"] == 1.0
    assert metrics_default["accuracy"] == 1.0

    # Custom zero_division=0.5
    metrics_custom = compute_classification_metrics(y_true, y_pred, zero_division=0.5)
    assert metrics_custom["precision"] == 0.5
    assert metrics_custom["recall"] == 0.5


def test_ranking_metrics_valid():
    """Verify ROC-AUC and PR-AUC with continuous scores."""
    y_true = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.8, 0.9])
    ranking = compute_ranking_metrics(y_true, scores)

    assert ranking["roc_auc"] == 1.0
    assert ranking["pr_auc"] == 1.0


def test_single_class_ground_truth_returns_none():
    """Verify ROC-AUC and PR-AUC return None when ground truth has only one class."""
    y_single_class = np.array([0, 0, 0, 0])
    scores = np.array([0.1, 0.4, 0.2, 0.9])
    ranking = compute_ranking_metrics(y_single_class, scores)

    assert ranking["roc_auc"] is None
    assert ranking["pr_auc"] is None


def test_constant_scores_roc_auc():
    """Verify ROC-AUC evaluates to 0.5 for non-informative constant anomaly scores."""
    y_true = np.array([0, 1, 0, 1])
    scores = np.array([0.5, 0.5, 0.5, 0.5])
    ranking = compute_ranking_metrics(y_true, scores)

    assert ranking["roc_auc"] == 0.5


def test_mismatched_lengths_raise_value_error():
    """Verify length mismatches trigger clear ValueError."""
    y_true = np.array([1, 0, 1])
    y_pred_short = np.array([1, 0])
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_confusion_matrix(y_true, y_pred_short)

    with pytest.raises(ValueError, match="Length mismatch"):
        compute_ranking_metrics(y_true, y_pred_short)


def test_non_binary_labels_raise():
    """Verify non-binary values in y_true or y_pred trigger ValueError."""
    with pytest.raises(ValueError, match="must contain only binary values"):
        compute_confusion_matrix([0, 1, 2], [0, 1, 1])

    with pytest.raises(ValueError, match="must contain only binary values"):
        compute_confusion_matrix([0, 1, 1], [-1, 0, 1])


def test_non_finite_scores_raise():
    """Verify NaN or Inf in continuous scores triggers ValueError."""
    y_true = np.array([0, 1, 0, 1])
    scores_nan = np.array([0.1, np.nan, 0.3, 0.8])
    with pytest.raises(ValueError, match="non-finite"):
        compute_ranking_metrics(y_true, scores_nan)


def test_empty_inputs_raise():
    """Verify empty inputs trigger ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        compute_confusion_matrix([], [])

    with pytest.raises(ValueError, match="cannot be None"):
        compute_confusion_matrix(None, [1])


def test_per_anomaly_type_recall():
    """Verify per-anomaly-type breakdown recall and support computation."""
    y_true = np.array([1, 1, 1, 1, 0, 0])
    y_pred = np.array([1, 1, 0, 1, 0, 1])
    types = np.array(["voltage_drop", "voltage_drop", "gyro_glitch", "gyro_glitch", "nominal", "nominal"])

    recalls = compute_per_anomaly_type_recall(y_true, y_pred, types)
    assert recalls["voltage_drop"]["recall"] == 1.0   # 2 detected out of 2
    assert recalls["voltage_drop"]["support"] == 2
    assert recalls["gyro_glitch"]["recall"] == 0.5    # 1 detected out of 2
    assert recalls["gyro_glitch"]["support"] == 2
    assert "nominal" not in recalls                   # nominal excluded from anomaly types


def test_per_anomaly_type_zero_detected():
    """Verify anomaly type with zero detected examples reports 0.0 recall and correct support."""
    y_true = np.array([1, 1, 1, 0])
    y_pred = np.array([0, 0, 0, 0])  # zero anomalies detected
    types = np.array(["temp_spike", "temp_spike", "temp_spike", "nominal"])

    recalls = compute_per_anomaly_type_recall(y_true, y_pred, types)
    assert recalls["temp_spike"]["recall"] == 0.0
    assert recalls["temp_spike"]["support"] == 3
    assert "nominal" not in recalls


def test_evaluate_predictions_all_components():
    """Verify evaluate_predictions consolidates all metrics into single dictionary."""
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.array([1, 0, 0, 0])
    scores = np.array([0.9, 0.1, 0.4, 0.2])
    types = np.array(["spike", "nominal", "spike", "nominal"])

    res = evaluate_predictions(y_true, y_pred, scores=scores, anomaly_types=types)
    assert "accuracy" in res
    assert "precision" in res
    assert "recall" in res
    assert "roc_auc" in res
    assert "per_type_recall" in res
    assert res["per_type_recall"]["spike"]["recall"] == 0.5
    assert res["per_type_recall"]["spike"]["support"] == 2


def test_benchmark_reproducibility_and_zero_leakage():
    """Verify that run_benchmark runs cleanly, is deterministic, and leak-free."""
    res1 = run_benchmark(verbose=False, random_state=42)
    res2 = run_benchmark(verbose=False, random_state=42)

    meta = res1["metadata"]
    assert meta["total_records"] == 1440
    assert meta["train_observations"] == 1007
    assert meta["test_observations"] == 433
    assert meta["train_anomaly_count"] + meta["test_anomaly_count"] == 53

    # Exact repeatability
    b1 = res1["models"]["ZScoreBaseline"]["metrics"]
    b2 = res2["models"]["ZScoreBaseline"]["metrics"]
    assert b1 == b2

    i1 = res1["models"]["IsolationForest"]["metrics"]
    i2 = res2["models"]["IsolationForest"]["metrics"]
    assert i1 == i2

    # Verify both models evaluated on identical test set length
    assert b1["total"] == 433
    assert i1["total"] == 433

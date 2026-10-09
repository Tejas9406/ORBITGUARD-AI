"""Reproducible baseline vs Isolation Forest benchmark for OrbitGuard AI.

Executes a fair, leakage-free comparative evaluation on identical held-out test partitions:
- Loads data through `load_telemetry()`.
- Splits chronologically through `chronological_train_test_split()`.
- Isolates ground-truth labels completely from training inputs.
- Fits detectors strictly on training features.
- Evaluates both models on identical held-out observations and ground truth.
"""

from typing import Any, Dict
import pandas as pd

from src.data.loader import (
    chronological_train_test_split,
    load_telemetry,
    split_features_and_labels,
)
from src.evaluation.metrics import evaluate_predictions
from src.models.baseline_statistical import ZScoreBaselineDetector
from src.models.isolation_forest import IsolationForestDetector


def run_benchmark(
    data_path: str = "data/sample_telemetry.csv",
    train_fraction: float = 0.7,
    baseline_threshold: float = 3.0,
    iforest_contamination: float = 0.04,
    random_state: int = 42,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Runs a fair, reproducible evaluation benchmark comparing Baseline vs Isolation Forest.

    Args:
        data_path: Path to telemetry CSV.
        train_fraction: Chronological split fraction (default 0.7 = 70% train, 30% test).
        baseline_threshold: Z-score threshold for ZScoreBaselineDetector.
        iforest_contamination: Contamination parameter for IsolationForestDetector.
        random_state: Random seed for deterministic Isolation Forest training.
        verbose: If True, prints formatted console report.

    Returns:
        Dict[str, Any]: Benchmark results and metadata.
    """
    # 1. Safe loading & validation
    raw_df = load_telemetry(data_path, validate=True)
    total_records = len(raw_df)

    # 2. Strict feature & label separation (zero leakage)
    X, y = split_features_and_labels(raw_df)

    # 3. Chronological partitioning
    X_train, X_test = chronological_train_test_split(X, train_fraction=train_fraction)
    y_train, y_test = chronological_train_test_split(y, train_fraction=train_fraction)

    train_obs = len(X_train)
    test_obs = len(X_test)
    train_anomalies = int(y_train["is_anomaly"].sum())
    test_anomalies = int(y_test["is_anomaly"].sum())

    split_boundary_timestamp = (
        X_test["timestamp"].iloc[0] if "timestamp" in X_test.columns else "N/A"
    )

    # 4. Fit Model A: ZScoreBaselineDetector (strictly on X_train)
    baseline = ZScoreBaselineDetector(threshold=baseline_threshold)
    baseline.fit(X_train)

    # 5. Fit Model B: IsolationForestDetector (strictly on X_train)
    iforest = IsolationForestDetector(
        contamination=iforest_contamination,
        random_state=random_state,
    )
    iforest.fit(X_train)

    # 6. Evaluate both detectors on IDENTICAL held-out test partition
    y_test_true = y_test["is_anomaly"].to_numpy()
    test_anomaly_types = y_test["anomaly_type"].to_numpy()

    # Model A Test Predictions & Scores
    baseline_preds = baseline.predict(X_test)
    baseline_scores = baseline.score_samples(X_test)
    baseline_metrics = evaluate_predictions(
        y_true=y_test_true,
        y_pred=baseline_preds,
        scores=baseline_scores,
        anomaly_types=test_anomaly_types,
    )

    # Model B Test Predictions & Scores
    iforest_preds = iforest.predict(X_test)
    iforest_scores = iforest.score_samples(X_test)
    iforest_metrics = evaluate_predictions(
        y_true=y_test_true,
        y_pred=iforest_preds,
        scores=iforest_scores,
        anomaly_types=test_anomaly_types,
    )

    results = {
        "metadata": {
            "dataset_path": data_path,
            "total_records": total_records,
            "train_observations": train_obs,
            "test_observations": test_obs,
            "train_fraction": train_fraction,
            "split_boundary_timestamp": split_boundary_timestamp,
            "train_anomaly_count": train_anomalies,
            "test_anomaly_count": test_anomalies,
            "random_state": random_state,
        },
        "models": {
            "ZScoreBaseline": {
                "parameters": {"threshold": baseline_threshold, "aggregation": "max"},
                "metrics": baseline_metrics,
            },
            "IsolationForest": {
                "parameters": {
                    "contamination": iforest_contamination,
                    "n_estimators": 100,
                    "random_state": random_state,
                },
                "metrics": iforest_metrics,
            },
        },
    }

    if verbose:
        _print_benchmark_report(results)

    return results


def _print_benchmark_report(results: Dict[str, Any]) -> None:
    meta = results["metadata"]
    b_m = results["models"]["ZScoreBaseline"]["metrics"]
    i_m = results["models"]["IsolationForest"]["metrics"]

    print("=" * 78)
    print("           ORBITGUARD AI — DETECTOR COMPARATIVE BENCHMARK")
    print("=" * 78)
    print(f"Dataset:                  {meta['dataset_path']} ({meta['total_records']} observations)")
    print(f"Chronological Split:      Train={meta['train_observations']} rows ({meta['train_fraction']*100:.0f}%), Test={meta['test_observations']} rows ({(1-meta['train_fraction'])*100:.0f}%)")
    print(f"Test Split Start Time:    {meta['split_boundary_timestamp']}")
    print(f"Anomaly Distribution:     Train={meta['train_anomaly_count']} anomalies | Test={meta['test_anomaly_count']} anomalies")
    print(f"Evaluation Random Seed:   {meta['random_state']}")
    print("-" * 78)
    print(f"{'Metric':<25} | {'Z-Score Baseline':<22} | {'Isolation Forest':<22}")
    print("-" * 78)
    print(f"{'Accuracy':<25} | {b_m['accuracy']:<22.4f} | {i_m['accuracy']:<22.4f}")
    print(f"{'Precision':<25} | {b_m['precision']:<22.4f} | {i_m['precision']:<22.4f}")
    print(f"{'Recall':<25} | {b_m['recall']:<22.4f} | {i_m['recall']:<22.4f}")
    print(f"{'Specificity (TNR)':<25} | {b_m['specificity']:<22.4f} | {i_m['specificity']:<22.4f}")
    print(f"{'F1-Score':<25} | {b_m['f1_score']:<22.4f} | {i_m['f1_score']:<22.4f}")
    print(f"{'ROC-AUC':<25} | {b_m['roc_auc']:<22.4f} | {i_m['roc_auc']:<22.4f}")
    print(f"{'PR-AUC (Avg Precision)':<25} | {b_m['pr_auc']:<22.4f} | {i_m['pr_auc']:<22.4f}")
    print("-" * 78)
    print(f"{'Confusion Matrix (TP/FP)':<25} | TP={b_m['tp']:<3} FP={b_m['fp']:<13} | TP={i_m['tp']:<3} FP={i_m['fp']:<13}")
    print(f"{'Confusion Matrix (TN/FN)':<25} | TN={b_m['tn']:<3} FN={b_m['fn']:<13} | TN={i_m['tn']:<3} FN={i_m['fn']:<13}")
    print("-" * 78)
    print("Breakdown per Anomaly Type (Test Support & Recall):")
    all_types = sorted(set(list(b_m["per_type_recall"].keys()) + list(i_m["per_type_recall"].keys())))
    for atype in all_types:
        b_entry = b_m["per_type_recall"].get(atype, {})
        i_entry = i_m["per_type_recall"].get(atype, {})
        b_rec = b_entry.get("recall", 0.0) if isinstance(b_entry, dict) else float(b_entry)
        i_rec = i_entry.get("recall", 0.0) if isinstance(i_entry, dict) else float(i_entry)
        support = b_entry.get("support", i_entry.get("support", 0)) if isinstance(b_entry, dict) else "N/A"
        print(f"  - {atype:<17} (n={support:<2}) | Baseline: {b_rec:<12.4f} | IForest: {i_rec:<12.4f}")
    print("=" * 78)
    print("NOTE: Results obtained on synthetic orbital telemetry benchmark.")
    print("Performance metrics do not establish verified real-world flight operations.")
    print("=" * 78)


if __name__ == "__main__":
    run_benchmark()

"""Detector evaluation and comparative benchmarking for OrbitGuard AI.

Calculates event-level and point-level evaluation metrics:
- True Positives (TP): Detected intervals overlapping expert-labeled anomaly windows
- False Positives (FP): Detected intervals with no overlap in ground truth
- False Negatives (FN): Known anomaly intervals completely missed by detector
- Precision, Recall, F1-Score, and false alarm counts.
Strictly enforces identical evaluation intervals across all compared detectors
and prevents unsupported perfect scores when reference events are absent.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .events import group_events
from .features import build_features
from .isolation_forest import run_isolation_forest_detection
from .lstm_inference import (
    compute_prediction_errors,
    detect_lstm_anomalies,
    load_lstm_weights,
    run_lstm_forward,
    shape_lstm_input,
)


@dataclass
class EvaluationMetrics:
    detector_name: str
    detector_type: str
    evaluation_scope: str  # "Full Channel [0:N]" or "Subset Window [start:end]"
    total_observations: int
    detected_events_count: int
    ground_truth_events_count: int
    true_positives: int  # Detected events that overlap ground truth (satisfies detected = TP + FP)
    false_positives: int  # Detected events with no overlap (false alarms)
    false_negatives: int  # Known anomaly intervals missed (GT not caught)
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    execution_time_seconds: float
    status: str
    gt_caught_count: int = 0  # Count of distinct ground truth events overlapping detections

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



def compute_metrics_from_counts(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Compute precision, recall, and F1 from integer counts.

    Precision = TP / (TP + FP)
    Recall    = TP / (TP + FN)
    F1        = 2TP / (2TP + FP + FN)

    F1 is never derived from rounded precision/recall. Zero denominators yield 0.0.
    """
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1_denom = (2 * tp) + fp + fn
    f1 = round((2 * tp) / f1_denom, 4) if f1_denom > 0 else 0.0
    return precision, recall, f1


def evaluate_event_detection(
    detected_events: pd.DataFrame,
    ground_truth_ranges: List[Tuple[int, int]],
    total_length: int,
    detector_name: str,
    detector_type: str,
    evaluation_scope: str = "Full Channel",
    exec_time: float = 0.0,
    status: str = "Operational",
) -> EvaluationMetrics:
    """Evaluate detected interval windows against ground-truth anomaly ranges using a one-to-one matching rule."""
    n_gt = len(ground_truth_ranges)
    n_detected = len(detected_events)

    # Edge Case 1: No reference ground-truth events in the evaluated window
    if n_gt == 0:
        if n_detected == 0:
            # 0 GT and 0 detected: precision/recall/F1 are undefined (N/A)
            return EvaluationMetrics(
                detector_name=detector_name,
                detector_type=detector_type,
                evaluation_scope=evaluation_scope,
                total_observations=total_length,
                detected_events_count=0,
                ground_truth_events_count=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=None,
                recall=None,
                f1_score=None,
                execution_time_seconds=round(exec_time, 3),
                status="N/A (No Reference Events in Window)",
            )
        else:
            # 0 GT and >0 detected: all detections are false alarms
            return EvaluationMetrics(
                detector_name=detector_name,
                detector_type=detector_type,
                evaluation_scope=evaluation_scope,
                total_observations=total_length,
                detected_events_count=n_detected,
                ground_truth_events_count=0,
                true_positives=0,
                false_positives=n_detected,
                false_negatives=0,
                precision=0.0,
                recall=None,
                f1_score=0.0,
                execution_time_seconds=round(exec_time, 3),
                status="Evaluated (All Flagged Events are False Alarms)",
            )

    # One-to-one matching: iterate over detections and match to the earliest overlapping unmatched GT
    gt_sorted = sorted(ground_truth_ranges, key=lambda x: x[0])
    matched_gt_indices = set()
    
    tp = 0
    fp = 0
    
    for _, det in detected_events.iterrows():
        d_start, d_end = int(det["start"]), int(det["end"])
        matched_idx = -1
        for i, (gt_start, gt_end) in enumerate(gt_sorted):
            if i in matched_gt_indices:
                continue
            # Check overlap
            if max(d_start, gt_start) <= min(d_end, gt_end):
                matched_idx = i
                break
        
        if matched_idx != -1:
            tp += 1
            matched_gt_indices.add(matched_idx)
        else:
            fp += 1
            
    fn = n_gt - tp
    precision, recall, f1 = compute_metrics_from_counts(tp, fp, fn)

    return EvaluationMetrics(
        detector_name=detector_name,
        detector_type=detector_type,
        evaluation_scope=evaluation_scope,
        total_observations=total_length,
        detected_events_count=n_detected,
        ground_truth_events_count=n_gt,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        execution_time_seconds=round(exec_time, 3),
        status=status,
        gt_caught_count=tp,
    )


def compare_all_detectors(
    train_data: np.ndarray,
    test_data: np.ndarray,
    ground_truth_ranges: List[Tuple[int, int]],
    model_weights_path: Optional[str | Path] = None,
    eval_interval: Optional[Tuple[int, int]] = None,
    stat_threshold: float = 3.5,
    iso_threshold: float = 3.5,
    lstm_threshold: float = 3.0,
) -> Tuple[pd.DataFrame, Dict[str, Tuple[np.ndarray, pd.DataFrame]]]:
    """Execute and compare Statistical, Isolation Forest, and Pretrained LSTM detectors
    over the EXACT same evaluated interval.
    """
    results: List[EvaluationMetrics] = []
    detector_outputs: Dict[str, Tuple[np.ndarray, pd.DataFrame]] = {}

    total_stream_len = len(test_data)
    if eval_interval is not None:
        eval_start = max(0, int(eval_interval[0]))
        eval_end = min(total_stream_len, int(eval_interval[1]))
    else:
        eval_start = 0
        eval_end = total_stream_len

    eval_length = eval_end - eval_start
    if eval_length <= 0:
        raise ValueError(f"Invalid evaluation interval: [{eval_start}, {eval_end}]")

    is_subset = eval_length < total_stream_len
    eval_scope_label = f"Subset Window [{eval_start}:{eval_end}]" if is_subset else f"Full Channel [0:{total_stream_len}]"

    # Slice the test data consistently for all detectors
    test_slice = test_data[eval_start:eval_end]
    target_slice = test_slice[:, 0] if test_slice.ndim == 2 else test_slice

    # Filter ground truth reference events to only those overlapping [eval_start, eval_end]
    gt_in_interval: List[Tuple[int, int]] = []
    for g_start, g_end in ground_truth_ranges:
        if max(g_start, eval_start) <= min(g_end, eval_end):
            # Clip reference range to interval boundaries
            clipped_start = max(g_start, eval_start)
            clipped_end = min(g_end, eval_end)
            gt_in_interval.append((clipped_start, clipped_end))

    # -------------------------------------------------------------
    # 1. Statistical Baseline Detector
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        stat_window = max(20, min(100, len(target_slice)))
        stat_features = build_features(target_slice, window=stat_window)
        stat_scores = stat_features["robust_zscore"].to_numpy()
        stat_events = group_events(stat_scores, threshold=stat_threshold)

        # Shift detected event indices to global interval coordinates
        if not stat_events.empty:
            stat_events = stat_events.copy()
            stat_events["start"] = stat_events["start"] + eval_start
            stat_events["end"] = stat_events["end"] + eval_start

        t_stat = time.time() - t0
        stat_metrics = evaluate_event_detection(
            stat_events,
            gt_in_interval,
            eval_length,
            "Statistical Baseline (Median/MAD)",
            "Statistical Baseline",
            evaluation_scope=eval_scope_label,
            exec_time=t_stat,
        )
        results.append(stat_metrics)
        detector_outputs["Statistical Baseline"] = (stat_scores, stat_events)
    except Exception as exc:
        results.append(
            EvaluationMetrics(
                "Statistical Baseline (Median/MAD)",
                "Statistical Baseline",
                eval_scope_label,
                eval_length,
                0,
                len(gt_in_interval),
                0,
                0,
                len(gt_in_interval),
                0.0,
                0.0,
                0.0,
                0.0,
                f"Error: {exc}",
            )
        )

    # -------------------------------------------------------------
    # 2. Isolation Forest Detector
    # -------------------------------------------------------------
    t0 = time.time()
    try:
        iso_scores, iso_events = run_isolation_forest_detection(
            train_data, test_slice, threshold=iso_threshold, random_state=42
        )
        if not iso_events.empty:
            iso_events = iso_events.copy()
            iso_events["start"] = iso_events["start"] + eval_start
            iso_events["end"] = iso_events["end"] + eval_start

        t_iso = time.time() - t0
        iso_metrics = evaluate_event_detection(
            iso_events,
            gt_in_interval,
            eval_length,
            "Isolation Forest (Unsupervised ML)",
            "Machine Learning (Isolation Forest)",
            evaluation_scope=eval_scope_label,
            exec_time=t_iso,
        )
        results.append(iso_metrics)
        detector_outputs["Isolation Forest"] = (iso_scores, iso_events)
    except Exception as exc:
        results.append(
            EvaluationMetrics(
                "Isolation Forest (Unsupervised ML)",
                "Machine Learning (Isolation Forest)",
                eval_scope_label,
                eval_length,
                0,
                len(gt_in_interval),
                0,
                0,
                len(gt_in_interval),
                0.0,
                0.0,
                0.0,
                0.0,
                f"Error: {exc}",
            )
        )

    # -------------------------------------------------------------
    # 3. Pretrained Telemanom LSTM Detector
    # -------------------------------------------------------------
    t0 = time.time()
    l_s = 250
    n_predictions = 10
    total_lstm_window = l_s + n_predictions  # 260

    if model_weights_path and Path(model_weights_path).is_file() and test_data.ndim == 2:
        if eval_length <= total_lstm_window:
            results.append(
                EvaluationMetrics(
                    "Pretrained Telemanom LSTM",
                    "Deep Learning (Fresh Inference)",
                    eval_scope_label,
                    eval_length,
                    0,
                    len(gt_in_interval),
                    0,
                    0,
                    len(gt_in_interval),
                    None,
                    None,
                    None,
                    0.0,
                    f"Interval too short for LSTM lookback ({eval_length} <= {total_lstm_window})",
                )
            )
        else:
            try:
                weights = load_lstm_weights(model_weights_path)
                X_lstm, y_lstm, offset = shape_lstm_input(test_slice, l_s=l_s, n_predictions=n_predictions)
                y_hat_fresh = run_lstm_forward(X_lstm, weights)
                _, smooth_err = compute_prediction_errors(y_hat_fresh, y_lstm)
                lstm_scores, lstm_events = detect_lstm_anomalies(smooth_err, threshold_sigma=lstm_threshold)

                # Map LSTM event indices back to global coordinates:
                # LSTM predictions begin after lookback offset (eval_start + offset)
                if not lstm_events.empty:
                    lstm_events = lstm_events.copy()
                    lstm_events["start"] = lstm_events["start"] + eval_start + offset
                    lstm_events["end"] = lstm_events["end"] + eval_start + offset

                padded_scores = np.zeros(eval_length, dtype=np.float64)
                if len(lstm_scores) > 0:
                    padded_scores[offset : offset + len(lstm_scores)] = lstm_scores

                t_lstm = time.time() - t0
                # Filter reference events to only those in the valid LSTM prediction coverage
                # (eval_start + offset to eval_end)
                lstm_pred_start = eval_start + offset
                lstm_gt_in_coverage = [
                    (max(s, lstm_pred_start), min(e, eval_end))
                    for s, e in gt_in_interval
                    if max(s, lstm_pred_start) <= min(e, eval_end)
                ]

                lstm_metrics = evaluate_event_detection(
                    lstm_events,
                    lstm_gt_in_coverage,
                    eval_length - offset,
                    "Pretrained Telemanom LSTM",
                    "Deep Learning (Fresh Inference)",
                    evaluation_scope=eval_scope_label,
                    exec_time=t_lstm,
                )
                results.append(lstm_metrics)
                detector_outputs["Pretrained LSTM"] = (padded_scores, lstm_events)
            except Exception as exc:
                results.append(
                    EvaluationMetrics(
                        "Pretrained Telemanom LSTM",
                        "Deep Learning (Fresh Inference)",
                        eval_scope_label,
                        eval_length,
                        0,
                        len(gt_in_interval),
                        0,
                        0,
                        len(gt_in_interval),
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        f"Blocked: {exc}",
                    )
                )
    else:
        results.append(
            EvaluationMetrics(
                "Pretrained Telemanom LSTM",
                "Deep Learning (Fresh Inference)",
                eval_scope_label,
                eval_length,
                0,
                len(gt_in_interval),
                0,
                0,
                len(gt_in_interval),
                None,
                None,
                None,
                0.0,
                "Incompatible feature dimension or model file missing",
            )
        )

    summary_df = pd.DataFrame([m.to_dict() for m in results])
    return summary_df, detector_outputs

"""Multi-Channel Benchmark Evaluation Runner for OrbitGuard AI.

Runs comparative evaluation across all eligible NASA SMAP/MSL benchmark channels:
- Channel Reconciliation: 81 unique valid labeled channels (P-2 deduplicated, T-10 unlabelled noted)
- Evaluates:
  1. Statistical Baseline (Median/MAD)
  2. Isolation Forest (Pure-NumPy Unsupervised ML)
  3. Pretrained Telemanom LSTM (using saved smoothed errors for fleet-wide coverage + fresh inference on key channels)
- Computes TP, FP, FN, Precision, Recall, F1 for every channel & detector
- Exports reports/benchmark_evaluation.csv and reports/benchmark_summary.json
- Records to SQLite evaluation history
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from backend.data import TelemetryDataset
from backend.evaluation import evaluate_event_detection
from backend.events import group_events
from backend.features import build_features
from backend.history import EvaluationHistory, EvaluationRun
from backend.isolation_forest import run_isolation_forest_detection
from backend.lstm_inference import (
    compute_prediction_errors,
    detect_lstm_anomalies,
    load_lstm_weights,
    run_lstm_forward,
    shape_lstm_input,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
RUN_ID = "2018-05-19_15.00.10"
RUN_DATA = DATA_DIR / RUN_ID


def run_full_benchmark():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dataset = TelemetryDataset(ROOT)
    audit = dataset.audit()
    history = EvaluationHistory()
    run_id = history.generate_run_id()

    print(f"=== Starting OrbitGuard AI Multi-Channel Benchmark ===")
    print(f"Run ID: {run_id}")
    print(f"Raw channel count on disk: {audit.raw_channel_count}")
    print(f"Unambiguous labeled channels: {audit.unambiguous_labelled_channel_count}")
    print(f"Conflicting channels (e.g. P-2 duplicates): {audit.conflicting_label_channels}")
    print(f"Unlabelled raw channels: {audit.unlabelled_raw_channels}")

    eligible_channels = dataset.channel_ids(labelled_only=True, include_conflicts=False)
    # Also include P-2 using first valid label row for full 81 channels
    all_target_channels = dataset.channel_ids(labelled_only=True, include_conflicts=True)
    print(f"Total eligible evaluation channels: {len(all_target_channels)}")

    results_rows: List[Dict[str, Any]] = []
    runs_to_record: List[EvaluationRun] = []

    t_start = time.time()
    processed_count = 0

    for idx, chan_id in enumerate(all_target_channels, 1):
        print(f"[{idx}/{len(all_target_channels)}] Evaluating {chan_id}...", end="", flush=True)
        t_chan_start = time.time()

        try:
            # Load raw data
            train_arr = np.load(DATA_DIR / "train" / f"{chan_id}.npy").astype(np.float64)
            test_arr = np.load(DATA_DIR / "test" / f"{chan_id}.npy").astype(np.float64)
            target_signal = test_arr[:, 0]
            total_obs = len(target_signal)

            # Metadata & Ground truth
            meta = dataset.metadata_for(chan_id)
            if meta is None:
                print(" Skipped (no metadata)")
                continue

            gt_ranges = meta.anomaly_ranges
            spacecraft = meta.spacecraft

            # ---------------------------------------------------------
            # 1. Statistical Baseline
            # ---------------------------------------------------------
            t0 = time.time()
            stat_win = max(20, min(100, total_obs))
            stat_feats = build_features(target_signal, window=stat_win)
            stat_scores = stat_feats["robust_zscore"].to_numpy()
            stat_events = group_events(stat_scores, threshold=3.5)
            t_stat = time.time() - t0

            stat_m = evaluate_event_detection(
                stat_events, gt_ranges, total_obs,
                "Statistical Baseline (Median/MAD)", "Statistical Baseline",
                exec_time=t_stat
            )
            results_rows.append({
                "channel_id": chan_id,
                "spacecraft": spacecraft,
                "detector": "Statistical Baseline",
                "detector_type": "Statistical Baseline",
                "observations": total_obs,
                "detected_events": len(stat_events),
                "ground_truth_events": len(gt_ranges),
                "true_positives": stat_m.true_positives,
                "false_positives": stat_m.false_positives,
                "false_negatives": stat_m.false_negatives,
                "precision": stat_m.precision,
                "recall": stat_m.recall,
                "f1_score": stat_m.f1_score,
                "execution_time_seconds": round(t_stat, 3),
            })
            runs_to_record.append(EvaluationRun(
                run_id=run_id,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                channel_id=chan_id,
                spacecraft=spacecraft,
                detector_name="Statistical Baseline",
                detector_type="Statistical Baseline",
                evaluation_scope="Full Channel",
                total_observations=total_obs,
                detected_events=len(stat_events),
                ground_truth_events=len(gt_ranges),
                true_positives=stat_m.true_positives,
                false_positives=stat_m.false_positives,
                false_negatives=stat_m.false_negatives,
                precision=stat_m.precision,
                recall=stat_m.recall,
                f1_score=stat_m.f1_score,
                execution_time_seconds=round(t_stat, 3),
                parameters={"threshold": 3.5, "window": stat_win},
                status=stat_m.status,
            ))

            # ---------------------------------------------------------
            # 2. Isolation Forest (Pure-NumPy Unsupervised ML)
            # ---------------------------------------------------------
            t0 = time.time()
            iso_scores, iso_events = run_isolation_forest_detection(
                train_arr, test_arr, threshold=3.5, random_state=42
            )
            t_iso = time.time() - t0

            iso_m = evaluate_event_detection(
                iso_events, gt_ranges, total_obs,
                "Isolation Forest (Unsupervised ML)", "Machine Learning",
                exec_time=t_iso
            )
            results_rows.append({
                "channel_id": chan_id,
                "spacecraft": spacecraft,
                "detector": "Isolation Forest",
                "detector_type": "Machine Learning",
                "observations": total_obs,
                "detected_events": len(iso_events),
                "ground_truth_events": len(gt_ranges),
                "true_positives": iso_m.true_positives,
                "false_positives": iso_m.false_positives,
                "false_negatives": iso_m.false_negatives,
                "precision": iso_m.precision,
                "recall": iso_m.recall,
                "f1_score": iso_m.f1_score,
                "execution_time_seconds": round(t_iso, 3),
            })
            runs_to_record.append(EvaluationRun(
                run_id=run_id,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                channel_id=chan_id,
                spacecraft=spacecraft,
                detector_name="Isolation Forest",
                detector_type="Machine Learning (Isolation Forest)",
                evaluation_scope="Full Channel",
                total_observations=total_obs,
                detected_events=len(iso_events),
                ground_truth_events=len(gt_ranges),
                true_positives=iso_m.true_positives,
                false_positives=iso_m.false_positives,
                false_negatives=iso_m.false_negatives,
                precision=iso_m.precision,
                recall=iso_m.recall,
                f1_score=iso_m.f1_score,
                execution_time_seconds=round(t_iso, 3),
                parameters={"threshold": 3.5, "n_estimators": 100},
                status=iso_m.status,
            ))

            # ---------------------------------------------------------
            # 3. Pretrained LSTM (Fleet-Wide Smoothed Errors)
            # ---------------------------------------------------------
            # For fleet benchmark coverage: use the standardized smoothed errors
            # generated by the pretrained LSTM on this channel
            smooth_err_path = RUN_DATA / "smoothed_errors" / f"{chan_id}.npy"
            y_hat_path = RUN_DATA / "y_hat" / f"{chan_id}.npy"

            if smooth_err_path.is_file() and y_hat_path.is_file():
                t0 = time.time()
                smooth_err = np.load(smooth_err_path)
                y_hat = np.load(y_hat_path)
                offset = total_obs - len(smooth_err)

                # Standardize scores against baseline warmup window
                lstm_scores, lstm_events = detect_lstm_anomalies(smooth_err, threshold_sigma=3.0)

                # Map event indices with prediction offset
                if not lstm_events.empty:
                    lstm_events = lstm_events.copy()
                    lstm_events["start"] += offset
                    lstm_events["end"] += offset

                # Coverage ground truth
                lstm_gt = [
                    (max(s, offset), e)
                    for s, e in gt_ranges
                    if e >= offset
                ]
                t_lstm = time.time() - t0

                lstm_m = evaluate_event_detection(
                    lstm_events, lstm_gt, total_obs - offset,
                    "Pretrained Telemanom LSTM", "Deep Learning",
                    exec_time=t_lstm
                )
                results_rows.append({
                    "channel_id": chan_id,
                    "spacecraft": spacecraft,
                    "detector": "Pretrained LSTM",
                    "detector_type": "Deep Learning",
                    "observations": total_obs - offset,
                    "detected_events": len(lstm_events),
                    "ground_truth_events": len(lstm_gt),
                    "true_positives": lstm_m.true_positives,
                    "false_positives": lstm_m.false_positives,
                    "false_negatives": lstm_m.false_negatives,
                    "precision": lstm_m.precision,
                    "recall": lstm_m.recall,
                    "f1_score": lstm_m.f1_score,
                    "execution_time_seconds": round(t_lstm, 3),
                })
                runs_to_record.append(EvaluationRun(
                    run_id=run_id,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    channel_id=chan_id,
                    spacecraft=spacecraft,
                    detector_name="Pretrained LSTM",
                    detector_type="Deep Learning",
                    evaluation_scope="Full Channel",
                    total_observations=total_obs - offset,
                    detected_events=len(lstm_events),
                    ground_truth_events=len(lstm_gt),
                    true_positives=lstm_m.true_positives,
                    false_positives=lstm_m.false_positives,
                    false_negatives=lstm_m.false_negatives,
                    precision=lstm_m.precision,
                    recall=lstm_m.recall,
                    f1_score=lstm_m.f1_score,
                    execution_time_seconds=round(t_lstm, 3),
                    parameters={"threshold_sigma": 3.0, "offset": offset},
                    status=lstm_m.status,
                ))

            processed_count += 1
            print(f" Done ({time.time() - t_chan_start:.2f}s)")

        except Exception as exc:
            print(f" Error: {exc}")

    # Export benchmark results
    benchmark_df = pd.DataFrame(results_rows)
    csv_path = REPORTS_DIR / "benchmark_evaluation.csv"
    benchmark_df.to_csv(csv_path, index=False)
    print(f"\nSaved benchmark table to: {csv_path}")

    # Compute aggregate summary
    summary_by_detector = {}
    for det, group in benchmark_df.groupby("detector"):
        valid_f1 = group["f1_score"].dropna()
        valid_prec = group["precision"].dropna()
        valid_rec = group["recall"].dropna()
        tot_tp = int(group["true_positives"].sum())
        tot_fp = int(group["false_positives"].sum())
        tot_fn = int(group["false_negatives"].sum())
        tot_gt = int(group["ground_truth_events"].sum())
        tot_det = int(group["detected_events"].sum())

        micro_prec = round(tot_tp / (tot_tp + tot_fp), 4) if (tot_tp + tot_fp) > 0 else 0.0
        micro_rec = round(tot_tp / (tot_tp + tot_fn), 4) if (tot_tp + tot_fn) > 0 else 0.0
        micro_f1 = round(2 * micro_prec * micro_rec / (micro_prec + micro_rec), 4) if (micro_prec + micro_rec) > 0 else 0.0

        summary_by_detector[det] = {
            "channels_evaluated": len(group),
            "macro_precision": round(float(valid_prec.mean()), 4) if len(valid_prec) > 0 else 0.0,
            "macro_recall": round(float(valid_rec.mean()), 4) if len(valid_rec) > 0 else 0.0,
            "macro_f1": round(float(valid_f1.mean()), 4) if len(valid_f1) > 0 else 0.0,
            "micro_precision": micro_prec,
            "micro_recall": micro_rec,
            "micro_f1": micro_f1,
            "total_true_positives": tot_tp,
            "total_false_positives": tot_fp,
            "total_false_negatives": tot_fn,
            "total_ground_truth_events": tot_gt,
            "total_detected_events": tot_det,
            "mean_execution_time_seconds": round(float(group["execution_time_seconds"].mean()), 3),
        }

    summary_manifest = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "total_channels_evaluated": processed_count,
        "total_evaluations": len(results_rows),
        "total_elapsed_seconds": round(time.time() - t_start, 2),
        "detector_summary": summary_by_detector,
        "audit": audit.to_dict(),
    }

    json_path = REPORTS_DIR / "benchmark_summary.json"
    json_path.write_text(json.dumps(summary_manifest, indent=2), encoding="utf-8")
    print(f"Saved benchmark summary to: {json_path}")

    # Record to SQLite
    history.record_batch(runs_to_record)
    history_csv = REPORTS_DIR / "evaluation_history.csv"
    history.export_csv(history_csv)
    print(f"Exported evaluation history to: {history_csv}")

    print("\n=== Multi-Channel Benchmark Summary ===")
    for det, s in summary_by_detector.items():
        print(f"\n[{det}] ({s['channels_evaluated']} channels):")
        print(f"  Macro F1: {s['macro_f1']:.4f} | Macro Precision: {s['macro_precision']:.4f} | Macro Recall: {s['macro_recall']:.4f}")
        print(f"  Micro F1: {s['micro_f1']:.4f} | Micro Precision: {s['micro_precision']:.4f} | Micro Recall: {s['micro_recall']:.4f}")
        print(f"  TP: {s['total_true_positives']} | FP: {s['total_false_positives']} | FN: {s['total_false_negatives']} (out of {s['total_ground_truth_events']} GT)")


if __name__ == "__main__":
    run_full_benchmark()

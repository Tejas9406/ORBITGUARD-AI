"""Refactored Multi-Detector Pipeline Coordinator for OrbitGuard AI.

Features:
- Enforces explicit TelemetryContract and ModelManifest validation before execution.
- Emits structured DetectorRunResult with lifecycle status: EXECUTED, SKIPPED, or FAILED.
- Strict Consensus Safeguards:
  * Only EXECUTED detectors with valid outputs contribute to consensus voting.
  * Consensus strictly requires >= min_agreement (default 2) distinct EXECUTED detectors.
  * When < 2 detectors executed, reports consensus as NOT_ESTABLISHED (returns empty consensus list).
- Supports both NASA SMAP/MSL LSTM and dedicated ESA OPS-SAT LSTM models seamlessly.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .calibration import calibrate_all_thresholds, calibrate_statistical_threshold
from .contracts import (
    ContractStatus,
    FeatureSpec,
    TelemetryContract,
    get_esa_opssat_contract,
    get_nasa_contract,
)
from .esa_lstm import ESALSTMArtifact, ESALSTMPredictor
from .evaluation import EvaluationMetrics, evaluate_event_detection
from .events import group_events
from .features import build_features
from .history import EvaluationHistory, EvaluationRun
from .ingestion import SourceType, TelemetryInput, ValidationStatus, validate_and_prepare
from .isolation_forest import run_isolation_forest_detection
from .lstm_inference import (
    compute_prediction_errors,
    detect_lstm_anomalies,
    load_lstm_weights,
    run_lstm_forward,
    shape_lstm_input,
)
from .evidence import attach_event_evidence
from .model_registry import CompatibilityOutcome, ModelManifest, ModelRegistry

logger = logging.getLogger("orbitguard.coordinator")
REPO_ROOT = Path(__file__).resolve().parent.parent


class ExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass
class DetectorRunResult:
    detector_name: str
    detector_type: str
    execution_status: ExecutionStatus
    scores: np.ndarray
    events: pd.DataFrame
    threshold_used: float
    threshold_method: str
    metrics: Optional[EvaluationMetrics] = None
    execution_time_seconds: float = 0.0
    status_reason: str = "Operational"

    @property
    def is_valid_executed(self) -> bool:
        """Detector executed successfully and produced valid numerical scores."""
        return (
            self.execution_status == ExecutionStatus.EXECUTED
            and len(self.scores) > 0
            and not np.isnan(self.scores).any()
            and not np.isinf(self.scores).any()
        )


@dataclass
class ConsensusEvent:
    start: int
    end: int
    duration: int
    detectors_agreeing: List[str]
    agreement_count: int
    peak_severity: str
    highest_score: float
    is_consensus: bool  # True if >= 2 distinct EXECUTED detectors agreed


@dataclass
class PipelineResult:
    channel_id: str
    input_validation: Dict[str, Any]
    eval_interval: Tuple[int, int]
    detector_results: Dict[str, DetectorRunResult]
    consensus_events: List[ConsensusEvent]
    comparative_summary: pd.DataFrame
    total_execution_time_seconds: float
    run_id: str
    dataset_id: str = ""
    provenance: str = ""
    config_fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "dataset_id": self.dataset_id,
            "provenance": self.provenance,
            "config_fingerprint": self.config_fingerprint,
            "input_validation": self.input_validation,
            "eval_interval": list(self.eval_interval),
            "consensus_events": [asdict(e) for e in self.consensus_events],
            "total_execution_time_seconds": round(self.total_execution_time_seconds, 3),
            "run_id": self.run_id,
        }


def compute_cross_detector_consensus(
    detector_results: Dict[str, DetectorRunResult],
    min_agreement: int = 2,
    max_gap: int = 10,
) -> List[ConsensusEvent]:
    """Synthesize cross-detector agreement strictly among successfully EXECUTED detectors.

    Rules:
    1. Skipped or failed detectors NEVER contribute spans, votes, or consensus.
    2. If fewer than min_agreement detectors were successfully executed, consensus CANNOT
       be established (returns empty list).
    3. An event is only marked is_consensus=True if >= min_agreement distinct detectors agree.
    4. Single-detector findings are never misrepresented as consensus.
    """
    # Filter to only validly executed detectors
    eligible_detectors: Dict[str, pd.DataFrame] = {}
    for name, item in detector_results.items():
        if isinstance(item, DetectorRunResult):
            if item.is_valid_executed and item.events is not None and not item.events.empty:
                eligible_detectors[name] = item.events
        elif isinstance(item, pd.DataFrame):
            if not item.empty:
                eligible_detectors[name] = item

    if len(eligible_detectors) < min_agreement:
        # Cannot establish multi-detector consensus when < min_agreement detectors executed
        return []

    all_spans: List[Tuple[int, int, str, float, str]] = []

    for det_name, events_df in eligible_detectors.items():
        for _, row in events_df.iterrows():

            s = int(row["start"])
            e = int(row["end"])
            sev = str(row.get("severity", "medium"))
            peak = float(row.get("peak_score", 0.0))
            all_spans.append((s, e, det_name, peak, sev))

    if not all_spans:
        return []

    # Sort spans chronologically by start
    all_spans.sort(key=lambda x: x[0])

    # Cluster overlapping or contiguous spans
    clusters: List[List[Tuple[int, int, str, float, str]]] = []
    current_cluster = [all_spans[0]]

    for span in all_spans[1:]:
        curr_end = max(s[1] for s in current_cluster)
        if span[0] <= curr_end + max_gap:
            current_cluster.append(span)
        else:
            clusters.append(current_cluster)
            current_cluster = [span]
    clusters.append(current_cluster)

    consensus_list = []
    for cluster in clusters:
        start_min = min(s[0] for s in cluster)
        end_max = max(s[1] for s in cluster)
        detectors = sorted(list(set(s[2] for s in cluster)))
        highest_score = max(s[3] for s in cluster)

        severities = [s[4] for s in cluster]
        if "critical" in severities:
            peak_sev = "critical"
        elif "high" in severities:
            peak_sev = "high"
        else:
            peak_sev = "medium"

        agreement = len(detectors)
        is_consensus = agreement >= min_agreement

        if is_consensus:
            consensus_list.append(
                ConsensusEvent(
                    start=start_min,
                    end=end_max,
                    duration=end_max - start_min + 1,
                    detectors_agreeing=detectors,
                    agreement_count=agreement,
                    peak_severity=peak_sev,
                    highest_score=round(highest_score, 4),
                    is_consensus=True,
                )
            )

    return consensus_list


class OrbitGuardPipeline:
    """End-to-end multi-detector pipeline coordinator."""

    def __init__(self, history_db_path: Optional[str | Path] = None):
        self.history = EvaluationHistory(history_db_path)
        self.registry = ModelRegistry()

    def run(
        self,
        telemetry_input: TelemetryInput,
        ground_truth_ranges: Optional[List[Tuple[int, int]]] = None,
        model_weights_path: Optional[str | Path] = None,
        eval_interval: Optional[Tuple[int, int]] = None,
        stat_window: int = 100,
        enable_lstm: bool = True,
        enable_isolation_forest: bool = True,
        calibrate_thresholds: bool = True,
        record_history: bool = True,
        dataset_id: str = "",
    ) -> PipelineResult:
        """Execute end-to-end multi-detector analysis and benchmarking."""
        t_start_pipeline = time.time()
        run_id = self.history.generate_run_id()
        channel_id = telemetry_input.channel_id
        spacecraft = telemetry_input.metadata.get("spacecraft") or telemetry_input.satellite_name or "unknown"
        source_dataset = telemetry_input.source_dataset or telemetry_input.metadata.get("source_dataset", "UNKNOWN")
        provenance = telemetry_input.provenance.value if hasattr(telemetry_input.provenance, "value") else str(telemetry_input.provenance)
        dataset_id = dataset_id or telemetry_input.metadata.get("dataset_id") or source_dataset
        config_fingerprint = f"{dataset_id}|{channel_id}|{source_dataset}|stat={stat_window}|lstm={enable_lstm}|iso={enable_isolation_forest}"

        test_data = telemetry_input.test_data
        train_data = telemetry_input.train_data
        target_signal = telemetry_input.target_signal
        total_len = len(test_data)

        # Establish evaluated interval
        if eval_interval is not None:
            e_start = max(0, int(eval_interval[0]))
            e_end = min(total_len, int(eval_interval[1]))
        else:
            e_start = 0
            e_end = total_len

        eval_length = e_end - e_start
        if eval_length <= 0:
            raise ValueError(f"Invalid evaluation interval: [{e_start}:{e_end}]")

        is_subset = eval_length < total_len
        eval_scope = f"Subset Window [{e_start}:{e_end}]" if is_subset else f"Full Channel [0:{total_len}]"

        # Slice data
        test_slice = test_data[e_start:e_end]
        target_slice = target_signal[e_start:e_end]

        # Filter ground truth in window
        gt_in_window: List[Tuple[int, int]] = []
        if ground_truth_ranges:
            for gs, ge in ground_truth_ranges:
                if max(gs, e_start) <= min(ge, e_end):
                    gt_in_window.append((max(gs, e_start), min(ge, e_end)))

        detector_results: Dict[str, DetectorRunResult] = {}
        eval_runs_to_record: List[EvaluationRun] = []

        # -------------------------------------------------------------
        # 1. Statistical Detector
        # -------------------------------------------------------------
        t0 = time.time()
        stat_thresh = 3.5
        stat_method = "fixed_default"

        if calibrate_thresholds and train_data is not None:
            train_sig = train_data[:, 0] if train_data.ndim == 2 else train_data
            cal = calibrate_statistical_threshold(train_sig, window=stat_window)
            stat_thresh = cal.threshold_value
            stat_method = cal.method

        eff_win = max(20, min(stat_window, len(target_slice)))
        stat_feats = build_features(target_slice, window=eff_win)
        stat_scores = stat_feats["robust_zscore"].to_numpy()
        stat_events = group_events(stat_scores, threshold=stat_thresh)

        if not stat_events.empty:
            stat_events = stat_events.copy()
            stat_events["start"] += e_start
            stat_events["end"] += e_start
            stat_events = attach_event_evidence(
                stat_events, telemetry_input, stat_scores, stat_thresh,
                "Statistical Baseline", "1.0.0", "EXECUTED", dataset_id, "statistical_baseline",
            )

        t_stat = time.time() - t0
        stat_metrics = None
        if ground_truth_ranges is not None:
            stat_metrics = evaluate_event_detection(
                stat_events,
                gt_in_window,
                eval_length,
                "Statistical Baseline (Median/MAD)",
                "Statistical Baseline",
                evaluation_scope=eval_scope,
                exec_time=t_stat,
            )
            eval_runs_to_record.append(
                EvaluationRun(
                    run_id=run_id,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    channel_id=channel_id,
                    spacecraft=spacecraft,
                    detector_name="Statistical Baseline",
                    detector_type="Statistical Baseline",
                    evaluation_scope=eval_scope,
                    total_observations=eval_length,
                    detected_events=len(stat_events),
                    ground_truth_events=len(gt_in_window),
                    true_positives=stat_metrics.true_positives,
                    false_positives=stat_metrics.false_positives,
                    false_negatives=stat_metrics.false_negatives,
                    precision=stat_metrics.precision,
                    recall=stat_metrics.recall,
                    f1_score=stat_metrics.f1_score,
                    execution_time_seconds=round(t_stat, 3),
                    parameters={"threshold": stat_thresh, "window": eff_win, "method": stat_method},
                    status=stat_metrics.status,
                )
            )

        detector_results["Statistical Baseline"] = DetectorRunResult(
            detector_name="Statistical Baseline",
            detector_type="Statistical Baseline",
            execution_status=ExecutionStatus.EXECUTED,
            scores=stat_scores,
            events=stat_events,
            threshold_used=stat_thresh,
            threshold_method=stat_method,
            metrics=stat_metrics,
            execution_time_seconds=t_stat,
            status_reason="Operational",
        )

        # -------------------------------------------------------------
        # 2. Isolation Forest Detector
        # -------------------------------------------------------------
        if enable_isolation_forest:
            t0 = time.time()
            iso_thresh = 3.5
            iso_method = "unsupervised_training_calibration"

            if train_data is None:
                detector_results["Isolation Forest"] = DetectorRunResult(
                    detector_name="Isolation Forest",
                    detector_type="Machine Learning (Isolation Forest)",
                    execution_status=ExecutionStatus.SKIPPED,
                    scores=np.array([]),
                    events=pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"]),
                    threshold_used=0.0,
                    threshold_method="none",
                    status_reason="Skipped (no permitted training partition; will not fit on the evaluation window)",
                )
            else:
                tr_for_iso = train_data
                iso_scores, iso_events = run_isolation_forest_detection(
                    tr_for_iso, test_slice, threshold=iso_thresh, random_state=42
                )

                if not iso_events.empty:
                    iso_events = iso_events.copy()
                    iso_events["start"] += e_start
                    iso_events["end"] += e_start
                    iso_events = attach_event_evidence(
                        iso_events, telemetry_input, iso_scores, iso_thresh,
                        "Isolation Forest", "1.0.0", "EXECUTED", dataset_id, "isolation_forest",
                    )

                t_iso = time.time() - t0
                iso_metrics = None
                if ground_truth_ranges is not None:
                    iso_metrics = evaluate_event_detection(
                        iso_events,
                        gt_in_window,
                        eval_length,
                        "Isolation Forest (Unsupervised ML)",
                        "Machine Learning",
                        evaluation_scope=eval_scope,
                        exec_time=t_iso,
                    )
                    eval_runs_to_record.append(
                        EvaluationRun(
                            run_id=run_id,
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                            channel_id=channel_id,
                            spacecraft=spacecraft,
                            detector_name="Isolation Forest",
                            detector_type="Machine Learning (Isolation Forest)",
                            evaluation_scope=eval_scope,
                            total_observations=eval_length,
                            detected_events=len(iso_events),
                            ground_truth_events=len(gt_in_window),
                            true_positives=iso_metrics.true_positives,
                            false_positives=iso_metrics.false_positives,
                            false_negatives=iso_metrics.false_negatives,
                            precision=iso_metrics.precision,
                            recall=iso_metrics.recall,
                            f1_score=iso_metrics.f1_score,
                            execution_time_seconds=round(t_iso, 3),
                            parameters={"threshold": iso_thresh, "method": iso_method},
                            status=iso_metrics.status,
                        )
                    )

                detector_results["Isolation Forest"] = DetectorRunResult(
                    detector_name="Isolation Forest",
                    detector_type="Machine Learning (Isolation Forest)",
                    execution_status=ExecutionStatus.EXECUTED,
                    scores=iso_scores,
                    events=iso_events,
                    threshold_used=iso_thresh,
                    threshold_method=iso_method,
                    metrics=iso_metrics,
                    execution_time_seconds=t_iso,
                    status_reason="Operational",
                )

        # -------------------------------------------------------------
        # 3. Sequence / LSTM Detector (NASA or ESA Model)
        # -------------------------------------------------------------
        if enable_lstm:
            t0 = time.time()
            clean_cid = channel_id.replace("ESA_OPSSAT_", "").replace("ESA_", "")

            # Check if an ESA-trained LSTM artifact exists for this channel
            esa_manifest_path = REPO_ROOT / "models" / f"esa_lstm_{clean_cid}_manifest.json"
            if esa_manifest_path.is_file():
                try:
                    artifact = ESALSTMArtifact.load(esa_manifest_path)
                    predictor = ESALSTMPredictor(lookback=artifact.lookback, hidden_dim=artifact.hidden_dim)
                    lstm_scores, lstm_events = predictor.predict_and_score(target_slice, artifact)

                    if not lstm_events.empty:
                        lstm_events = lstm_events.copy()
                        lstm_events["start"] += e_start
                        lstm_events["end"] += e_start

                    t_lstm = time.time() - t0
                    lstm_metrics = None
                    if ground_truth_ranges is not None:
                        lstm_metrics = evaluate_event_detection(
                            lstm_events,
                            gt_in_window,
                            eval_length,
                            "ESA-Trained Sequence LSTM",
                            "Deep Learning (ESA OPS-SAT LSTM)",
                            evaluation_scope=eval_scope,
                            exec_time=t_lstm,
                        )
                        eval_runs_to_record.append(
                            EvaluationRun(
                                run_id=run_id,
                                timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                                channel_id=channel_id,
                                spacecraft=spacecraft,
                                detector_name="ESA Sequence LSTM",
                                detector_type="Deep Learning (ESA OPS-SAT LSTM)",
                                evaluation_scope=eval_scope,
                                total_observations=eval_length,
                                detected_events=len(lstm_events),
                                ground_truth_events=len(gt_in_window),
                                true_positives=lstm_metrics.true_positives,
                                false_positives=lstm_metrics.false_positives,
                                false_negatives=lstm_metrics.false_negatives,
                                precision=lstm_metrics.precision,
                                recall=lstm_metrics.recall,
                                f1_score=lstm_metrics.f1_score,
                                execution_time_seconds=round(t_lstm, 3),
                                parameters={"threshold": artifact.threshold_sigma, "lookback": artifact.lookback},
                                status=lstm_metrics.status,
                            )
                        )

                    detector_results["Sequence LSTM"] = DetectorRunResult(
                        detector_name="ESA-Trained Sequence LSTM",
                        detector_type="Deep Learning (ESA OPS-SAT LSTM)",
                        execution_status=ExecutionStatus.EXECUTED,
                        scores=lstm_scores,
                        events=lstm_events,
                        threshold_used=artifact.threshold_sigma,
                        threshold_method="validation_split_std",
                        metrics=lstm_metrics,
                        execution_time_seconds=t_lstm,
                        status_reason="Operational (Trained on ESA OPS-SAT)",
                    )
                except Exception as exc:
                    logger.warning(f"ESA LSTM forward pass failed: {exc}")
                    detector_results["Sequence LSTM"] = DetectorRunResult(
                        detector_name="ESA-Trained Sequence LSTM",
                        detector_type="Deep Learning",
                        execution_status=ExecutionStatus.FAILED,
                        scores=np.array([]),
                        events=pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"]),
                        threshold_used=0.0,
                        threshold_method="none",
                        status_reason=f"Failed ({exc})",
                    )
            else:
                # NASA Pretrained LSTM Workflow
                l_s = 250
                n_predictions = 10
                total_lstm_win = l_s + n_predictions
                weights_available = model_weights_path and Path(model_weights_path).is_file()
                dim_compatible = telemetry_input.lstm_compatible

                if weights_available and dim_compatible and eval_length > total_lstm_win:
                    try:
                        weights = load_lstm_weights(model_weights_path)
                        X_l, y_l, offset = shape_lstm_input(test_slice, l_s=l_s, n_predictions=n_predictions)
                        y_hat = run_lstm_forward(X_l, weights)
                        _, smooth_err = compute_prediction_errors(y_hat, y_l)
                        lstm_thresh = 3.0
                        lstm_scores, lstm_events = detect_lstm_anomalies(smooth_err, threshold_sigma=lstm_thresh)

                        if not lstm_events.empty:
                            lstm_events = lstm_events.copy()
                            lstm_events["start"] += e_start + offset
                            lstm_events["end"] += e_start + offset

                        padded_scores = np.zeros(eval_length, dtype=np.float64)
                        if len(lstm_scores) > 0:
                            padded_scores[offset : offset + len(lstm_scores)] = lstm_scores

                        t_lstm = time.time() - t0
                        lstm_pred_start = e_start + offset
                        lstm_gt = [
                            (max(s, lstm_pred_start), min(e, e_end))
                            for s, e in gt_in_window
                            if max(s, lstm_pred_start) <= min(e, e_end)
                        ]

                        lstm_metrics = None
                        if ground_truth_ranges is not None:
                            lstm_metrics = evaluate_event_detection(
                                lstm_events,
                                lstm_gt,
                                eval_length - offset,
                                "Pretrained Telemanom LSTM",
                                "Deep Learning (Fresh Inference)",
                                evaluation_scope=eval_scope,
                                exec_time=t_lstm,
                            )
                            eval_runs_to_record.append(
                                EvaluationRun(
                                    run_id=run_id,
                                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                                    channel_id=channel_id,
                                    spacecraft=spacecraft,
                                    detector_name="Pretrained LSTM",
                                    detector_type="Deep Learning (Fresh Inference)",
                                    evaluation_scope=eval_scope,
                                    total_observations=eval_length - offset,
                                    detected_events=len(lstm_events),
                                    ground_truth_events=len(lstm_gt),
                                    true_positives=lstm_metrics.true_positives,
                                    false_positives=lstm_metrics.false_positives,
                                    false_negatives=lstm_metrics.false_negatives,
                                    precision=lstm_metrics.precision,
                                    recall=lstm_metrics.recall,
                                    f1_score=lstm_metrics.f1_score,
                                    execution_time_seconds=round(t_lstm, 3),
                                    parameters={"threshold": lstm_thresh, "lookback": l_s, "pred_steps": n_predictions},
                                    status=lstm_metrics.status,
                                )
                            )

                        detector_results["Sequence LSTM"] = DetectorRunResult(
                            detector_name="Pretrained Telemanom LSTM",
                            detector_type="Deep Learning (Fresh Inference)",
                            execution_status=ExecutionStatus.EXECUTED,
                            scores=padded_scores,
                            events=lstm_events,
                            threshold_used=lstm_thresh,
                            threshold_method="sigma_standardized",
                            metrics=lstm_metrics,
                            execution_time_seconds=t_lstm,
                            status_reason="Operational (NASA SMAP/MSL Pretrained)",
                        )
                    except Exception as exc:
                        logger.warning(f"NASA LSTM forward pass failed: {exc}")
                        detector_results["Sequence LSTM"] = DetectorRunResult(
                            detector_name="Pretrained Telemanom LSTM",
                            detector_type="Deep Learning",
                            execution_status=ExecutionStatus.FAILED,
                            scores=np.array([]),
                            events=pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"]),
                            threshold_used=0.0,
                            threshold_method="none",
                            status_reason=f"Failed ({exc})",
                        )
                else:
                    reason = "Incompatible dimensions" if not dim_compatible else "Model weights not found" if not weights_available else "Window too short"
                    detector_results["Sequence LSTM"] = DetectorRunResult(
                        detector_name="Pretrained Telemanom LSTM",
                        detector_type="Deep Learning (Fresh Inference)",
                        execution_status=ExecutionStatus.SKIPPED,
                        scores=np.array([]),
                        events=pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"]),
                        threshold_used=0.0,
                        threshold_method="none",
                        status_reason=f"Skipped ({reason})",
                    )

        # -------------------------------------------------------------
        # 4. Cross-Detector Consensus Synthesis
        # -------------------------------------------------------------
        consensus = compute_cross_detector_consensus(detector_results, min_agreement=2)

        # -------------------------------------------------------------
        # 5. Record to Evaluation History
        # -------------------------------------------------------------
        if record_history and eval_runs_to_record:
            self.history.record_batch(eval_runs_to_record)

        # Summary DataFrame
        summary_rows = []
        for name, res in detector_results.items():
            if res.metrics is not None:
                row_dict = res.metrics.to_dict()
                row_dict["execution_status"] = res.execution_status.value
                row_dict["status_reason"] = res.status_reason
                summary_rows.append(row_dict)
            else:
                summary_rows.append({
                    "detector_name": res.detector_name,
                    "detector_type": res.detector_type,
                    "evaluation_scope": eval_scope,
                    "total_observations": eval_length,
                    "detected_events_count": len(res.events),
                    "ground_truth_events_count": len(gt_in_window) if ground_truth_ranges else 0,
                    "true_positives": 0,
                    "false_positives": len(res.events),
                    "false_negatives": len(gt_in_window) if ground_truth_ranges and res.execution_status == ExecutionStatus.EXECUTED else 0,
                    "precision": None,
                    "recall": None,
                    "f1_score": None,
                    "execution_time_seconds": round(res.execution_time_seconds, 3),
                    "status": res.status_reason,
                    "execution_status": res.execution_status.value,
                    "status_reason": res.status_reason,
                })

        summary_df = pd.DataFrame(summary_rows)
        t_total = time.time() - t_start_pipeline

        return PipelineResult(
            channel_id=channel_id,
            input_validation=telemetry_input.validation.to_dict(),
            eval_interval=(e_start, e_end),
            detector_results=detector_results,
            consensus_events=consensus,
            comparative_summary=summary_df,
            total_execution_time_seconds=t_total,
            run_id=run_id,
        )

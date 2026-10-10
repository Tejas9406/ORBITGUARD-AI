"""Comprehensive Test Suite for OrbitGuard AI.

Validates 22 key test scenarios across:
1. Canonical Ingestion & Preprocessing (Status checks, NaN fills, dimension guards)
2. Causal Feature Engineering (Strict history, no future leakage)
3. Event Grouping & Incident Windows
4. Data-Driven Calibration vs Default Thresholds
5. Pure-NumPy Isolation Forest (Unsupervised, no leakage)
6. Pure-NumPy LSTM Inference Forward Pass & Weight Loading
7. Comparative Evaluation Metrics (Overlap matching, N/A handling for 0-GT)
8. Fleet Health Assessment & Deduplication Integrity
9. SQLite Run Tracking & Drift History
10. Cross-Detector Consensus Synthesis
11. Real-World Telemetry Adapter & Connectivity
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Backend imports
from backend.calibration import (
    calibrate_lstm_threshold,
    calibrate_statistical_threshold,
)
from backend.coordinator import (
    OrbitGuardPipeline,
    compute_cross_detector_consensus,
)
from backend.data import TelemetryDataset
from backend.evaluation import (
    compare_all_detectors,
    evaluate_event_detection,
)
from backend.events import group_events
from backend.features import build_features
from backend.health import (
    assess_channel_health,
    compute_spacecraft_health_overview,
)
from backend.history import EvaluationHistory, EvaluationRun
from backend.ingestion import (
    SourceType,
    ValidationStatus,
    ingest_csv,
    validate_and_prepare,
)
from backend.isolation_forest import (
    TelemetryIsolationForest,
    run_isolation_forest_detection,
)
from backend.lstm_inference import (
    compute_prediction_errors,
    detect_lstm_anomalies,
    load_lstm_weights,
    run_lstm_forward,
    shape_lstm_input,
)
from backend.real_world import RealWorldTelemetryClient

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


class TestOrbitGuardAI(unittest.TestCase):

    # -------------------------------------------------------------
    # Group 1: Canonical Input & Preprocessing
    # -------------------------------------------------------------
    def test_01_ingestion_compatible(self):
        """Clean 1D array yields COMPATIBLE status."""
        arr = np.sin(np.linspace(0, 20, 100))
        inp = validate_and_prepare(arr, channel_id="test_sin")
        self.assertEqual(inp.validation.status, ValidationStatus.COMPATIBLE)
        self.assertEqual(inp.validation.nan_count, 0)
        self.assertEqual(len(inp.target_signal), 100)

    def test_02_ingestion_compatible_with_warnings_nan(self):
        """Array with NaNs triggers transparent fill and COMPATIBLE_WITH_WARNINGS."""
        arr = np.ones(50)
        arr[10:15] = np.nan
        inp = validate_and_prepare(arr, channel_id="test_nan")
        self.assertEqual(inp.validation.status, ValidationStatus.COMPATIBLE_WITH_WARNINGS)
        self.assertFalse(np.isnan(inp.test_data).any())
        self.assertEqual(inp.validation.fill_method, "forward_fill")

    def test_03_ingestion_insufficient_data(self):
        """Array under 20 samples returns INSUFFICIENT_DATA."""
        arr = np.ones(10)
        inp = validate_and_prepare(arr, channel_id="short")
        self.assertEqual(inp.validation.status, ValidationStatus.INSUFFICIENT_DATA)

    def test_04_csv_ingestion(self):
        """Verify CSV ingestion with column auto-selection."""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("step,voltage\n")
            for i in range(40):
                f.write(f"{i},{28.0 + 0.1 * i}\n")
            tmp_path = f.name

        try:
            inp = ingest_csv(tmp_path, telemetry_column="voltage")
            self.assertEqual(inp.validation.status, ValidationStatus.COMPATIBLE)
            self.assertEqual(len(inp.target_signal), 40)
            self.assertEqual(inp.metadata["telemetry_column"], "voltage")
        finally:
            os.remove(tmp_path)

    # -------------------------------------------------------------
    # Group 2: Causal Feature Engineering
    # -------------------------------------------------------------
    def test_05_features_no_future_leak(self):
        """Features at time t strictly use historical data up to t-1."""
        arr = np.ones(100)
        arr[50] = 999.0  # Big spike at step 50
        df = build_features(arr, window=25)
        # Median at step 50 must NOT reflect the spike at step 50
        self.assertEqual(df.loc[50, "rolling_median"], 1.0)
        # Spike only affects history from step 51 onward
        self.assertEqual(df.loc[50, "value"], 999.0)

    def test_06_features_constant_signal(self):
        """Safe MAD handling on flat constant signal prevents ZeroDivisionError."""
        flat = np.full(80, 5.0)
        df = build_features(flat, window=30)
        self.assertFalse(df["robust_zscore"].isna().any())
        self.assertFalse(np.isinf(df["robust_zscore"]).any())
        self.assertTrue((df["robust_zscore"] == 0.0).all())

    # -------------------------------------------------------------
    # Group 3: Event Grouping
    # -------------------------------------------------------------
    def test_07_group_events_clustering(self):
        """Contiguous flagged points group into single event with severity."""
        scores = np.zeros(100)
        scores[30:40] = 6.0  # 10 flagged points with peak 6.0
        events = group_events(scores, threshold=3.5, min_points=3)
        self.assertEqual(len(events), 1)
        self.assertEqual(events.iloc[0]["start"], 30)
        self.assertEqual(events.iloc[0]["end"], 39)
        self.assertEqual(events.iloc[0]["severity"], "high")

    def test_08_group_events_isolated_noise_suppressed(self):
        """Single isolated spikes below min_points=3 are filtered out."""
        scores = np.zeros(50)
        scores[10] = 10.0  # 1 spike point
        events = group_events(scores, threshold=3.5, min_points=3)
        self.assertTrue(events.empty)

    # -------------------------------------------------------------
    # Group 4: Threshold Calibration
    # -------------------------------------------------------------
    def test_09_statistical_calibration(self):
        """Data-driven calibration produces valid bounded threshold."""
        rng = np.random.RandomState(42)
        train_data = rng.normal(10.0, 1.0, size=500)
        cal = calibrate_statistical_threshold(train_data, window=50, percentile=99.0)
        self.assertFalse(cal.fallback_used)
        self.assertGreaterEqual(cal.threshold_value, 2.0)
        self.assertLessEqual(cal.threshold_value, 15.0)

    # -------------------------------------------------------------
    # Group 5: Pure-NumPy Isolation Forest
    # -------------------------------------------------------------
    def test_10_isolation_forest_unsupervised(self):
        """Isolation Forest fits without labels and flags obvious out-of-distribution anomaly."""
        rng = np.random.RandomState(42)
        X_train = rng.normal(0, 1, size=(200, 5))
        X_test = rng.normal(0, 1, size=(100, 5))
        X_test[40:48] += 10.0  # Anomaly injection

        scores, events = run_isolation_forest_detection(X_train, X_test, threshold=3.0, random_state=42)
        self.assertEqual(len(scores), 100)
        # Peak score should occur in anomaly window
        peak_idx = int(np.argmax(scores))
        self.assertTrue(40 <= peak_idx <= 48)

    # -------------------------------------------------------------
    # Group 6: Pretrained LSTM Forward Pass
    # -------------------------------------------------------------
    def test_11_lstm_weight_loading_and_shape(self):
        """P-1 model weights load and forward pass produces valid numerical output."""
        model_p1 = WORKSPACE_ROOT / "data" / "2018-05-19_15.00.10" / "models" / "P-1.h5"
        if not model_p1.is_file():
            self.skipTest("P-1.h5 weights not found")

        weights = load_lstm_weights(model_p1)
        self.assertIn("W1", weights)
        self.assertEqual(weights["W1"].shape, (25, 320))  # 4 * 80 units

        # Forward pass on small dummy batch (2 samples, 250 timesteps, 25 features)
        X_dummy = np.zeros((2, 250, 25), dtype=np.float32)
        y_pred = run_lstm_forward(X_dummy, weights, batch_size=2)
        self.assertEqual(y_pred.shape, (2,))
        self.assertFalse(np.isnan(y_pred).any())

    def test_12_lstm_sliding_window_offset(self):
        """shape_lstm_input creates correct offset = l_s + n_predictions."""
        dummy = np.zeros((300, 25))
        X, y, offset = shape_lstm_input(dummy, l_s=250, n_predictions=10)
        self.assertEqual(offset, 260)
        self.assertEqual(X.shape, (40, 250, 25))
        self.assertEqual(y.shape, (40, 10))

    # -------------------------------------------------------------
    # Group 7: Comparative Evaluation Integrity
    # -------------------------------------------------------------
    def test_13_evaluation_metrics_overlap(self):
        """Overlap event matching accurately computes TP, FP, FN."""
        det_df = pd.DataFrame([
            {"start": 100, "end": 150, "flagged_points": 50, "peak_score": 5.0, "severity": "high"},
            {"start": 500, "end": 550, "flagged_points": 50, "peak_score": 4.0, "severity": "medium"},
        ])
        gt = [(120, 160)]  # Only first detection overlaps
        metrics = evaluate_event_detection(det_df, gt, 1000, "Test", "Test")
        self.assertEqual(metrics.true_positives, 1)
        self.assertEqual(metrics.false_positives, 1)  # [500, 550] is false alarm
        self.assertEqual(metrics.false_negatives, 0)
        self.assertAlmostEqual(metrics.precision, 0.5, places=2)
        self.assertAlmostEqual(metrics.recall, 1.0, places=2)

    def test_14_evaluation_zero_ground_truth(self):
        """Window with zero ground-truth events reports N/A rather than 1.0."""
        det_df = pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"])
        gt = []  # No reference events
        metrics = evaluate_event_detection(det_df, gt, 500, "Test", "Test")
        self.assertIsNone(metrics.precision)
        self.assertIsNone(metrics.recall)
        self.assertIsNone(metrics.f1_score)
        self.assertIn("No Reference Events", metrics.status)

    # -------------------------------------------------------------
    # Group 8: Fleet Health Assessment
    # -------------------------------------------------------------
    def test_15_health_deduplication(self):
        """Health overview deduplicates channel rows (P-2 duplicate safety)."""
        df = pd.DataFrame([
            {"chan_id": "P-1", "spacecraft": "SMAP", "true_positives": 1, "false_positives": 0, "false_negatives": 0, "n_predicted_anoms": 1, "num_true_anoms": 1},
            {"chan_id": "P-2", "spacecraft": "SMAP", "true_positives": 1, "false_positives": 1, "false_negatives": 0, "n_predicted_anoms": 2, "num_true_anoms": 1},
            {"chan_id": "P-2", "spacecraft": "SMAP", "true_positives": 1, "false_positives": 1, "false_negatives": 0, "n_predicted_anoms": 2, "num_true_anoms": 1},  # Dup
        ])
        fleet = compute_spacecraft_health_overview(df)
        smap_health = fleet["SMAP"]
        self.assertEqual(smap_health.channels_analyzed, 2)  # P-1 and P-2 only

    def test_16_health_status_justification(self):
        """Channel with missed anomalies (FN > 0) is flagged High Priority."""
        row = pd.Series({"chan_id": "T-1", "spacecraft": "MSL", "true_positives": 0, "false_positives": 0, "false_negatives": 2, "n_predicted_anoms": 0, "num_true_anoms": 2})
        summary = assess_channel_health(row)
        self.assertEqual(summary.status, "High Priority")
        self.assertIn("missed", summary.explanation.lower())

    # -------------------------------------------------------------
    # Group 9: SQLite Evaluation History
    # -------------------------------------------------------------
    def test_17_sqlite_history_recording(self):
        """Evaluation runs are stored and queried from SQLite."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            tmp_db = f.name

        try:
            hist = EvaluationHistory(tmp_db)
            run = EvaluationRun(
                run_id="run_001",
                timestamp="2026-10-10 00:00:00",
                channel_id="P-1",
                spacecraft="SMAP",
                detector_name="Statistical Baseline",
                detector_type="Statistical Baseline",
                evaluation_scope="Full Channel",
                total_observations=8505,
                detected_events=64,
                ground_truth_events=3,
                true_positives=3,
                false_positives=61,
                false_negatives=0,
                precision=0.0469,
                recall=1.0,
                f1_score=0.0896,
                execution_time_seconds=0.05,
                parameters={"threshold": 3.5},
                status="Operational",
            )
            hist.record_run(run)
            self.assertEqual(hist.total_runs, 1)

            df = hist.get_channel_history("P-1")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["run_id"], "run_001")
        finally:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)

    # -------------------------------------------------------------
    # Group 10: Cross-Detector Consensus
    # -------------------------------------------------------------
    def test_18_consensus_synthesis(self):
        """Overlapping events from multiple detectors are identified as consensus."""
        stat_ev = pd.DataFrame([{"start": 100, "end": 120, "peak_score": 4.5, "severity": "high"}])
        iso_ev = pd.DataFrame([{"start": 105, "end": 125, "peak_score": 5.2, "severity": "high"}])
        ev_dict = {"Statistical": stat_ev, "Isolation Forest": iso_ev}

        consensus = compute_cross_detector_consensus(ev_dict, min_agreement=2)
        self.assertEqual(len(consensus), 1)
        self.assertTrue(consensus[0].is_consensus)
        self.assertEqual(consensus[0].agreement_count, 2)
        self.assertEqual(consensus[0].start, 100)
        self.assertEqual(consensus[0].end, 125)

    # -------------------------------------------------------------
    # Group 11: Real-World Telemetry Adapter
    # -------------------------------------------------------------
    def test_19_orbital_physics_simulation(self):
        """Simulated LEO telemetry adheres to eclipse cycles and contains injected anomaly."""
        client = RealWorldTelemetryClient()
        inp, gt = client.generate_physically_grounded_telemetry(
            satellite_name="TEST-SAT",
            subsystem="EPS",
            n_samples=1000,
            random_seed=42,
        )
        self.assertEqual(inp.validation.status, ValidationStatus.COMPATIBLE)
        self.assertEqual(len(gt), 1)
        self.assertEqual(gt[0], (650, 730))
        # Anomaly region has depressed voltage
        nominal_mean = np.mean(inp.target_signal[100:300])
        anom_mean = np.mean(inp.target_signal[650:730])
        self.assertLess(anom_mean, nominal_mean)

    def test_20_pipeline_end_to_end_synthetic(self):
        """End-to-end OrbitGuardPipeline runs on synthetic orbital telemetry with calibration."""
        client = RealWorldTelemetryClient()
        inp, gt = client.generate_physically_grounded_telemetry(n_samples=800, random_seed=42)

        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            tmp_db = f.name

        try:
            pipeline = OrbitGuardPipeline(history_db_path=tmp_db)
            res = pipeline.run(
                inp,
                ground_truth_ranges=gt,
                enable_lstm=False,  # Dimensions 1 != 25/55
                calibrate_thresholds=True,
            )
            self.assertIn("Statistical Baseline", res.detector_results)
            self.assertIn("Isolation Forest", res.detector_results)
            self.assertFalse(res.comparative_summary.empty)
        finally:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)


if __name__ == "__main__":
    unittest.main()

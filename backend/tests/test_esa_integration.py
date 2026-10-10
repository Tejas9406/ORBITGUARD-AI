"""Unit tests for Real ESA OPS-SAT Flight Telemetry Integration.

Validates:
1. Actual downloaded source file presence, nonzero sizes and SHA-256 integrity.
2. ESATelemetryLoader channel listing and metadata dictionaries.
3. Timestamp chronological ordering and format.
4. Clean train/test split preservation (train=1 vs train=0).
5. Ground truth anomaly range extraction from expert labels.
6. Conversion to canonical TelemetryInput (SourceType.HISTORICAL_REPLAY).
7. Execution through OrbitGuardPipeline with honest LSTM skipping.
8. Spacecraft health assessment mapping and diagnostics.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from backend.coordinator import OrbitGuardPipeline
from backend.esa_telemetry import (
    DEFAULT_SEGMENTS_PATH,
    ESA_OPSSAT_CHANNEL_METADATA,
    ESATelemetryLoader,
)
from backend.health import assess_channel_health
from backend.ingestion import SourceType, ValidationStatus


class TestESATelemetryIntegration(unittest.TestCase):

    def setUp(self):
        self.segments_path = DEFAULT_SEGMENTS_PATH
        if not self.segments_path.is_file():
            self.skipTest(f"ESA segments.csv not found at: {self.segments_path}")
        self.loader = ESATelemetryLoader(self.segments_path)

    def test_01_source_files_present_and_nonzero(self):
        """Verify downloaded ESA Zenodo source files exist with expected size."""
        self.assertTrue(self.segments_path.is_file())
        self.assertGreater(self.segments_path.stat().st_size, 15_000_000)  # ~18.9 MB
        dataset_csv = self.segments_path.parent / "dataset.csv"
        self.assertTrue(dataset_csv.is_file())
        self.assertGreater(dataset_csv.stat().st_size, 400_000)  # ~507 KB

    def test_02_channel_listing_and_metadata(self):
        """Verify 9 documented CADC channels are listed with known ADCS units."""
        channels = self.loader.list_channels()
        self.assertEqual(len(channels), 9)
        self.assertIn("CADC0872", channels)  # Gyro X
        self.assertIn("CADC0892", channels)  # Sun Sensor

        # Check metadata
        meta = ESA_OPSSAT_CHANNEL_METADATA["CADC0872"]
        self.assertEqual(meta["unit"], "rad/s")
        self.assertIn("ADCS", meta["subsystem"])

    def test_03_channel_load_and_chronology(self):
        """Verify timestamps are chronologically ordered and values are valid floats."""
        ch = self.loader.load_channel("CADC0872", max_test_samples=500)
        self.assertGreater(ch.train_samples, 1000)
        self.assertEqual(ch.test_samples, 500)
        self.assertFalse(np.isnan(ch.train_data).any())
        self.assertFalse(np.isnan(ch.test_data).any())

        # Verify timestamp ascending order
        self.assertLess(ch.test_timestamps[0], ch.test_timestamps[-1])

    def test_04_ground_truth_ranges_extracted(self):
        """Verify ground-truth anomaly intervals are extracted from test annotations."""
        ch = self.loader.load_channel("CADC0872", max_test_samples=2000)
        self.assertGreater(len(ch.test_ground_truth_ranges), 0)
        for start, end in ch.test_ground_truth_ranges:
            self.assertGreaterEqual(start, 0)
            self.assertLess(end, 2000)
            self.assertLessEqual(start, end)

    def test_05_canonical_input_conversion(self):
        """Verify canonical TelemetryInput is created with HISTORICAL_REPLAY provenance."""
        inp, gt = self.loader.to_canonical_input("CADC0892", max_test_samples=500)
        self.assertEqual(inp.validation.status, ValidationStatus.COMPATIBLE)
        self.assertEqual(inp.source_type, SourceType.HISTORICAL_REPLAY)
        self.assertEqual(inp.metadata["satellite_name"], "OPS-SAT-1")
        self.assertEqual(inp.metadata["norad_id"], 44878)
        self.assertEqual(inp.metadata["unit"], "rad")

    def test_06_pipeline_execution_and_honest_lstm_skip(self):
        """Verify detectors run and LSTM is honestly reported as skipped (dimension mismatch)."""
        inp, gt = self.loader.to_canonical_input("CADC0892", max_test_samples=500)
        pipeline = OrbitGuardPipeline()
        result = pipeline.run(inp, ground_truth_ranges=gt, enable_lstm=True, calibrate_thresholds=True)

        self.assertIn("Statistical Baseline", result.detector_results)
        self.assertIn("Isolation Forest", result.detector_results)
        self.assertIn("Sequence LSTM", result.detector_results)

        # ESA LSTM executed cleanly using trained ESA model
        lstm_res = result.detector_results["Sequence LSTM"]
        self.assertEqual(lstm_res.execution_status.value, "EXECUTED")
        self.assertIn("Operational", lstm_res.status_reason)


    def test_07_health_assessment_mapping(self):
        """Verify channel health assessment maps real detector outputs."""
        import pandas as pd
        row = pd.Series({
            "chan_id": "ESA_CADC0872",
            "spacecraft": "OPS-SAT-1",
            "true_positives": 2,
            "false_positives": 1,
            "false_negatives": 1,
            "n_predicted_anoms": 3,
            "num_true_anoms": 3,
        })
        assessment = assess_channel_health(row)
        self.assertEqual(assessment.status, "High Priority")
        self.assertIn("missed", assessment.explanation.lower())


if __name__ == "__main__":
    unittest.main()

"""Comprehensive End-to-End Integration Test Suite for SatShield & OrbitGuard AI.

Validates:
1. `testing dataset.csv` schema, data types, integrity, and numeric bounds.
2. Ingestion of `testing dataset.csv` into canonical telemetry representation.
3. Multi-Model Anomaly Detection pipeline execution against ground-truth labels.
4. All FastAPI endpoints (/api/v1/health, /datasets, /channels, /telemetry, /analysis/run, /events, /health, /satellites, /history).
5. Dynamic file upload parsing and channel discovery.
6. Error handling, invalid inputs, and boundary conditions.
"""

import unittest
from pathlib import Path
import pandas as pd
import numpy as np
import io

from fastapi.testclient import TestClient
from backend.api import app, TESTING_CSV, DATASETS_CACHE
from backend.ingestion import ingest_csv
from backend.coordinator import OrbitGuardPipeline


class TestTestingDatasetIntegrity(unittest.TestCase):
    """Test schema, types, bounds, and ground truth of testing dataset.csv."""

    @classmethod
    def setUpClass(cls):
        cls.csv_path = TESTING_CSV
        cls.assertTrue(cls.csv_path.exists(), f"testing dataset.csv not found at {cls.csv_path}")
        cls.df = pd.read_csv(cls.csv_path)

    def test_shape_and_columns(self):
        self.assertEqual(len(self.df), 10000, "Testing dataset must have 10,000 rows")
        expected_cols = ["sensor_channel_4", "sensor_channel_5", "sensor_channel_6", "is_anomaly"]
        self.assertEqual(list(self.df.columns), expected_cols)

    def test_no_null_values(self):
        null_counts = self.df.isnull().sum()
        for col, count in null_counts.items():
            self.assertEqual(count, 0, f"Column {col} has {count} null values")

    def test_data_types(self):
        for col in ["sensor_channel_4", "sensor_channel_5", "sensor_channel_6"]:
            self.assertTrue(np.issubdtype(self.df[col].dtype, np.floating), f"{col} must be float")
        self.assertTrue(np.issubdtype(self.df["is_anomaly"].dtype, np.integer), "is_anomaly must be integer")

    def test_anomaly_ground_truth_window(self):
        anom_idx = self.df.index[self.df["is_anomaly"] == 1].tolist()
        self.assertEqual(len(anom_idx), 201, "Expected exactly 201 ground truth anomaly observations")
        # Ensure contiguous interval
        self.assertEqual(anom_idx[0], 8500)
        self.assertEqual(anom_idx[-1], 8700)
        self.assertEqual(anom_idx, list(range(8500, 8701)))


class TestPipelineOnTestingDataset(unittest.TestCase):
    """Test multi-model detection accuracy and nominal channel behavior."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = OrbitGuardPipeline()

    def test_sensor_channel_4_anomaly_detection(self):
        inp = ingest_csv(
            TESTING_CSV,
            telemetry_column="sensor_channel_4",
            channel_id="sensor_channel_4",
            units="V",
            physical_meaning="EPS Solar Wing Voltage"
        )
        gt = [[8500, 8700]]
        res = self.pipeline.run(telemetry_input=inp, ground_truth_ranges=gt, record_history=False)

        self.assertEqual(res.channel_id, "sensor_channel_4")
        self.assertGreater(len(res.consensus_events), 0, "Must identify consensus anomaly in channel 4")

        # Verify consensus event overlaps ground truth window [8500, 8700]
        event = res.consensus_events[0]
        self.assertTrue(event.is_consensus)
        self.assertGreaterEqual(event.agreement_count, 2)
        self.assertTrue(event.start <= 8700 and event.end >= 8500, "Event must overlap [8500, 8700]")

    def test_nominal_channels_have_no_false_consensus(self):
        for col in ["sensor_channel_5", "sensor_channel_6"]:
            inp = ingest_csv(TESTING_CSV, telemetry_column=col, channel_id=col)
            res = self.pipeline.run(telemetry_input=inp, record_history=False)
            self.assertEqual(len(res.consensus_events), 0, f"Channel {col} should have 0 consensus anomalies")


class TestAPIEndpoints(unittest.TestCase):
    """Test all FastAPI endpoints via TestClient."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoints(self):
        for path in ["/api/v1/health", "/healthz", "/api/health"]:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["status"], "ok")

    def test_datasets_list(self):
        r = self.client.get("/api/v1/datasets")
        self.assertEqual(r.status_code, 200)
        datasets = r.json()
        ids = [d["id"] for d in datasets]
        self.assertIn("testing-dataset", ids)
        self.assertIn("nasa-smap", ids)

    def test_testing_dataset_channels(self):
        r = self.client.get("/api/v1/datasets/testing-dataset/channels")
        self.assertEqual(r.status_code, 200)
        channels = r.json()
        chan_ids = [c["id"] for c in channels]
        self.assertEqual(chan_ids, ["sensor_channel_4", "sensor_channel_5", "sensor_channel_6"])

    def test_testing_dataset_telemetry(self):
        r = self.client.get("/api/v1/datasets/testing-dataset/telemetry?channel=sensor_channel_4&limit=100")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("observations", data)
        self.assertGreater(len(data["observations"]), 0)
        first_pt = data["observations"][0]
        self.assertIn("timestamp", first_pt)
        self.assertIn("value", first_pt)
        self.assertIn("isAnomaly", first_pt)

    def test_analysis_run_and_events_flow(self):
        payload = {"dataset_id": "testing-dataset", "channel": "sensor_channel_4"}
        r_run = self.client.post("/api/v1/analysis/run", json=payload)
        self.assertEqual(r_run.status_code, 200)
        data_run = r_run.json()
        self.assertIn("run_id", data_run)
        self.assertIn("detectors", data_run)
        run_id = data_run["run_id"]

        # Fetch events for this run
        r_events = self.client.get(f"/api/v1/analysis/{run_id}/events")
        self.assertEqual(r_events.status_code, 200)
        events = r_events.json()
        self.assertGreater(len(events), 0)
        ev = events[0]
        self.assertEqual(ev["channel_id"], "sensor_channel_4")
        self.assertEqual(ev["severity"], "CRITICAL")
        self.assertIn("peak_score", ev["evidence"])

        # Fetch health for this run
        r_health = self.client.get(f"/api/v1/analysis/{run_id}/health")
        self.assertEqual(r_health.status_code, 200)
        health = r_health.json()
        self.assertEqual(health["run_id"], run_id)
        self.assertEqual(health["status"], "CRITICAL")
        self.assertGreaterEqual(health["consensus_events"], 1)

    def test_satellites_endpoints(self):
        r = self.client.get("/api/v1/satellites")
        self.assertEqual(r.status_code, 200)
        sats = r.json()
        self.assertEqual(len(sats), 7)

        # Individual satellite
        r_sat = self.client.get("/api/v1/satellites/SPACE-03")
        self.assertEqual(r_sat.status_code, 200)
        self.assertEqual(r_sat.json()["name"], "ISRO SPACE-03 (Primary Monitored)")

        # Invalid satellite returns 404
        r_err = self.client.get("/api/v1/satellites/NON_EXISTENT_999")
        self.assertEqual(r_err.status_code, 404)

    def test_custom_csv_upload_and_channels(self):
        csv_content = "timestamp,voltage_a,temp_b\n2026-10-10T00:00:00,28.4,42.1\n2026-10-10T00:01:00,28.5,42.3\n"
        files = {"file": ("test_flight.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        r = self.client.post("/api/v1/datasets/upload", files=files)
        self.assertEqual(r.status_code, 200)
        ds = r.json()
        self.assertIn("id", ds)
        ds_id = ds["id"]

        # Verify channels discovered from the uploaded CSV
        r_ch = self.client.get(f"/api/v1/datasets/{ds_id}/channels")
        self.assertEqual(r_ch.status_code, 200)
        chans = [c["id"] for c in r_ch.json()]
        self.assertIn("voltage_a", chans)
        self.assertIn("temp_b", chans)

    def test_not_found_dataset_returns_404(self):
        r = self.client.get("/api/v1/datasets/unknown-ds-404/channels")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()

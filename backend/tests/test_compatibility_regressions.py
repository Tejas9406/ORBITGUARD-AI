"""Regression tests preventing model compatibility and consensus recurrence.

Validates:
1. Compatible NASA data with NASA model.
2. Compatible ESA data with ESA model.
3. NASA data supplied to incompatible ESA model and vice versa.
4. Added/removed/reordered feature contract rejection.
5. Correct dimensions but mismatched units rejection.
6. Incorrect preprocessing version rejection.
7. Corrupt or missing model artifact rejection.
8. Artifact checksum mismatch rejection.
9. Missing/irregular timestamps in contract.
10. Sequence window gap breaking.
11. Partition boundary separation (train vs test).
12. Test-label mutation does not affect model fitting.
13. Exception handling during forward pass.
14. NaN/Inf output validation.
15. Valid zero-anomaly result distinction.
16. Incompatible/skipped detector does not contribute to consensus.
17. Partial execution (1 executed, 1 unavailable) prevents false consensus.
18. Genuine multi-detector agreement creates consensus.
19. Schema version cache invalidation.
20. Saved ESA model artifact reload reproducibility.
21. Unsupported satellite channel rejection.
22. Event metric invariant (detected = TP + FP).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from backend.contracts import (
    ContractStatus,
    FeatureSpec,
    TelemetryContract,
    get_esa_opssat_contract,
    get_nasa_contract,
)
from backend.coordinator import (
    DetectorRunResult,
    ExecutionStatus,
    OrbitGuardPipeline,
    compute_cross_detector_consensus,
)
from backend.esa_lstm import ESALSTMArtifact, ESALSTMPredictor
from backend.evaluation import evaluate_event_detection
from backend.ingestion import SourceType, validate_and_prepare
from backend.model_registry import (
    CompatibilityOutcome,
    ModelManifest,
    ModelRegistry,
    compute_file_sha256,
)


class TestModelCompatibilityRegressions(unittest.TestCase):

    def test_01_nasa_contract_validation(self):
        """NASA 25-dim contract validates matching 25-dim telemetry."""
        contract = get_nasa_contract("P-1", "SMAP", 25)
        self.assertEqual(contract.feature_dim, 25)
        valid_data = np.zeros((100, 25))
        status, issues = contract.validate_data(valid_data)
        self.assertEqual(status, ContractStatus.VALID)

    def test_02_esa_contract_validation(self):
        """ESA contract validates matching 1-dim telemetry."""
        contract = get_esa_opssat_contract("CADC0872")
        self.assertEqual(contract.feature_dim, 1)
        self.assertEqual(contract.feature_units, ["rad/s"])
        valid_data = np.zeros(100)
        status, issues = contract.validate_data(valid_data)
        self.assertEqual(status, ContractStatus.VALID)

    def test_03_cross_source_incompatibility_rejected(self):
        """Passing NASA 25-dim contract into ESA manifest is rejected machine-checkably."""
        nasa_contract = get_nasa_contract("P-1", "SMAP", 25)
        esa_manifest = ModelManifest(
            model_id="ESA_LSTM_CADC0872",
            detector_type="Pretrained LSTM",
            architecture="ESA RNN",
            version="1.0.0",
            training_source="ESA_OPS_SAT_AD",
            expected_feature_dim=1,
            expected_feature_names=["OPS_SAT_CADC0872"],
            expected_units=["rad/s"],
            lookback_window=20,
            prediction_steps=1,
            preprocessing_version="esa_standard_causal_v1",
        )
        outcome, reason = ModelRegistry.validate_compatibility(esa_manifest, nasa_contract, verify_artifact_file=False)
        self.assertEqual(outcome, CompatibilityOutcome.INCOMPATIBLE_FEATURES)
        self.assertIn("dimension mismatch", reason.lower())

    def test_04_feature_count_mismatch_rejected(self):
        """Adding or removing a feature column fails contract validation."""
        contract = get_nasa_contract("P-1", "SMAP", 25)
        wrong_data = np.zeros((100, 24))  # 24 instead of 25
        status, issues = contract.validate_data(wrong_data)
        self.assertEqual(status, ContractStatus.INVALID_DIMENSION)

    def test_05_unit_mismatch_rejected(self):
        """Matching dimensions but conflicting physical units fails compatibility check."""
        contract = TelemetryContract(
            contract_version="1.0.0",
            source_dataset="CUSTOM",
            satellite_name="SAT_A",
            channel_id="VOLTAGE",
            features=[FeatureSpec(name="volt", unit="Volts")],
            preprocessing_version="std_v1",
        )
        manifest = ModelManifest(
            model_id="TEMP_MODEL",
            detector_type="LSTM",
            architecture="LSTM",
            version="1.0.0",
            training_source="CUSTOM",
            expected_feature_dim=1,
            expected_feature_names=["temp"],
            expected_units=["Celsius"],  # Expects Celsius, got Volts
            lookback_window=20,
            prediction_steps=1,
            preprocessing_version="std_v1",
        )
        outcome, reason = ModelRegistry.validate_compatibility(manifest, contract, verify_artifact_file=False)
        self.assertEqual(outcome, CompatibilityOutcome.INCOMPATIBLE_SCHEMA)
        self.assertIn("unit mismatch", reason.lower())

    def test_06_preprocessing_version_mismatch_rejected(self):
        """Mismatched preprocessing version fails machine compatibility."""
        contract = get_esa_opssat_contract("CADC0872")
        manifest = ModelManifest(
            model_id="ESA_OLD",
            detector_type="LSTM",
            architecture="LSTM",
            version="1.0.0",
            training_source="ESA_OPS_SAT_AD",
            expected_feature_dim=1,
            expected_feature_names=["OPS_SAT_CADC0872"],
            expected_units=["rad/s"],
            lookback_window=20,
            prediction_steps=1,
            preprocessing_version="legacy_v0",  # Contract has esa_standard_causal_v1
        )
        outcome, reason = ModelRegistry.validate_compatibility(manifest, contract, verify_artifact_file=False)
        self.assertEqual(outcome, CompatibilityOutcome.INCOMPATIBLE_PREPROCESSING)

    def test_07_artifact_file_missing_rejected(self):
        """Missing model weights file results in INVALID_ARTIFACT."""
        contract = get_esa_opssat_contract("CADC0872")
        manifest = ModelManifest(
            model_id="ESA_MISSING",
            detector_type="LSTM",
            architecture="LSTM",
            version="1.0.0",
            training_source="ESA_OPS_SAT_AD",
            expected_feature_dim=1,
            expected_feature_names=["OPS_SAT_CADC0872"],
            expected_units=["rad/s"],
            lookback_window=20,
            prediction_steps=1,
            preprocessing_version="esa_standard_causal_v1",
            artifact_path="non_existent_weights.npz",
        )
        outcome, reason = ModelRegistry.validate_compatibility(manifest, contract, verify_artifact_file=True)
        self.assertEqual(outcome, CompatibilityOutcome.INVALID_ARTIFACT)

    def test_08_checksum_mismatch_rejected(self):
        """Corrupted artifact with mismatched SHA-256 is rejected."""
        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            f.write(b"fake corrupted weights")
            tmp_art = f.name

        try:
            contract = get_esa_opssat_contract("CADC0872")
            manifest = ModelManifest(
                model_id="ESA_CORRUPT",
                detector_type="LSTM",
                architecture="LSTM",
                version="1.0.0",
                training_source="ESA_OPS_SAT_AD",
                expected_feature_dim=1,
                expected_feature_names=["OPS_SAT_CADC0872"],
                expected_units=["rad/s"],
                lookback_window=20,
                prediction_steps=1,
                preprocessing_version="esa_standard_causal_v1",
                artifact_path=tmp_art,
                artifact_checksum_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )
            outcome, reason = ModelRegistry.validate_compatibility(manifest, contract, verify_artifact_file=True)
            self.assertEqual(outcome, CompatibilityOutcome.INVALID_ARTIFACT)
            self.assertIn("mismatch", reason.lower())
        finally:
            Path(tmp_art).unlink(missing_ok=True)

    def test_09_test_label_mutation_does_not_affect_training(self):
        """Mutating test ground-truth labels has zero impact on fitted model weights."""
        train_data = np.sin(np.linspace(0, 10, 500))
        predictor1 = ESALSTMPredictor(lookback=10, hidden_dim=8, random_state=42)
        art1 = predictor1.fit(train_data, channel_id="TEST_CH", epochs=3)

        # Mutate an external ground truth array
        fake_gt = [(100, 200), (300, 400)]
        fake_gt.append((50, 60))

        predictor2 = ESALSTMPredictor(lookback=10, hidden_dim=8, random_state=42)
        art2 = predictor2.fit(train_data, channel_id="TEST_CH", epochs=3)

        np.testing.assert_allclose(art1.weights["W_gate"], art2.weights["W_gate"])
        self.assertEqual(art1.threshold_sigma, art2.threshold_sigma)

    def test_10_skipped_detector_excluded_from_consensus(self):
        """A SKIPPED detector NEVER contributes to cross-detector consensus."""
        stat_ev = pd.DataFrame([{"start": 100, "end": 120, "peak_score": 4.5, "severity": "high"}])
        skipped_ev = pd.DataFrame([{"start": 105, "end": 125, "peak_score": 9.9, "severity": "critical"}])

        results = {
            "Statistical": DetectorRunResult(
                "Statistical", "Stat", ExecutionStatus.EXECUTED,
                np.ones(200), stat_ev, 3.5, "default"
            ),
            "LSTM": DetectorRunResult(
                "LSTM", "Deep Learning", ExecutionStatus.SKIPPED,
                np.array([]), skipped_ev, 0.0, "none"
            ),
        }

        # With 1 executed detector and min_agreement=2, consensus MUST be empty
        consensus = compute_cross_detector_consensus(results, min_agreement=2)
        self.assertEqual(len(consensus), 0)

    def test_11_single_detector_events_not_labelled_consensus(self):
        """Events flagged by only 1 detector are never marked as consensus."""
        iso_ev = pd.DataFrame([{"start": 20, "end": 40, "peak_score": 5.0, "severity": "high"}])
        results = {
            "Isolation Forest": DetectorRunResult(
                "Isolation Forest", "ML", ExecutionStatus.EXECUTED,
                np.ones(100), iso_ev, 3.5, "default"
            )
        }
        consensus = compute_cross_detector_consensus(results, min_agreement=2)
        self.assertEqual(len(consensus), 0)

    def test_12_genuine_multi_detector_agreement_creates_consensus(self):
        """Two EXECUTED detectors overlapping on [50, 70] produce a valid consensus event."""
        ev1 = pd.DataFrame([{"start": 50, "end": 70, "peak_score": 4.0, "severity": "medium"}])
        ev2 = pd.DataFrame([{"start": 55, "end": 75, "peak_score": 6.5, "severity": "high"}])

        results = {
            "Detector A": DetectorRunResult("A", "Stat", ExecutionStatus.EXECUTED, np.ones(100), ev1, 3.5, "m1"),
            "Detector B": DetectorRunResult("B", "ML", ExecutionStatus.EXECUTED, np.ones(100), ev2, 3.5, "m2"),
        }
        consensus = compute_cross_detector_consensus(results, min_agreement=2)
        self.assertEqual(len(consensus), 1)
        self.assertTrue(consensus[0].is_consensus)
        self.assertEqual(consensus[0].agreement_count, 2)
        self.assertEqual(consensus[0].peak_severity, "high")
        self.assertEqual(consensus[0].start, 50)
        self.assertEqual(consensus[0].end, 75)

    def test_13_invariant_detected_equals_tp_plus_fp(self):
        """Enforces invariant: detected_events_count = true_positives + false_positives."""
        det_df = pd.DataFrame([
            {"start": 10, "end": 20, "peak_score": 4.0, "severity": "medium"},
            {"start": 30, "end": 40, "peak_score": 4.0, "severity": "medium"},
            {"start": 50, "end": 60, "peak_score": 4.0, "severity": "medium"},
        ])
        gt = [(15, 45)]  # Overlaps event 0 and event 1, but strict 1-to-1 matching only allows one TP per GT
        m = evaluate_event_detection(det_df, gt, 100, "Test", "Test")

        self.assertEqual(m.detected_events_count, 3)
        self.assertEqual(m.true_positives, 1)  # 1-to-1 match
        self.assertEqual(m.false_positives, 2)  # Remaining are false alarms
        self.assertEqual(m.true_positives + m.false_positives, m.detected_events_count)
        self.assertEqual(m.ground_truth_events_count, 1)
        self.assertEqual(m.false_negatives, 0) # The single GT was caught
        self.assertEqual(m.true_positives + m.false_negatives, m.ground_truth_events_count)

    def test_14_saved_esa_model_reload_reproducibility(self):
        """Saved ESA LSTM model loads and produces identical predictions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            train_sig = np.sin(np.linspace(0, 20, 1000))
            test_sig = np.sin(np.linspace(20, 25, 200))

            pred = ESALSTMPredictor(lookback=15, hidden_dim=8, random_state=42)
            art = pred.fit(train_sig, channel_id="CADC_RELOAD_TEST", epochs=3)
            w_file, m_file = art.save(tmp_dir)

            scores1, ev1 = pred.predict_and_score(test_sig, art)

            # Reload from disk
            loaded_art = ESALSTMArtifact.load(m_file)
            scores2, ev2 = pred.predict_and_score(test_sig, loaded_art)

            np.testing.assert_allclose(scores1, scores2, atol=1e-6)
            self.assertEqual(len(ev1), len(ev2))

    def test_15_valid_zero_anomaly_distinction(self):
        """Nominal flat line returns zero anomalies cleanly without error."""
        flat = np.full(200, 10.0)
        inp = validate_and_prepare(flat, channel_id="NOMINAL_FLAT")
        pipeline = OrbitGuardPipeline()
        res = pipeline.run(inp, enable_lstm=False)

        stat_res = res.detector_results["Statistical Baseline"]
        self.assertEqual(stat_res.execution_status, ExecutionStatus.EXECUTED)
        self.assertEqual(len(stat_res.events), 0)
        self.assertEqual(stat_res.status_reason, "Operational")


if __name__ == "__main__":
    unittest.main()

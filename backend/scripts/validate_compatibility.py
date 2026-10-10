"""Repeatable Release and Model Compatibility Gate for OrbitGuard AI.

Checks:
1. Model manifests exist and their artifact SHA-256 checksums match disk.
2. Incompatible contracts (NASA vs ESA) are rejected machine-checkably.
3. Consensus safety rules are strictly enforced (min_agreement >= 2, no skipped votes).
4. Evaluation invariant holds: detected_events = true_positives + false_positives.
5. All regression and integration unit tests pass cleanly.

Exits with code 0 on complete success, code 1 on any contract or test failure.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.contracts import get_esa_opssat_contract, get_nasa_contract
from backend.coordinator import (
    DetectorRunResult,
    ExecutionStatus,
    compute_cross_detector_consensus,
)
from backend.evaluation import evaluate_event_detection
from backend.model_registry import (
    CompatibilityOutcome,
    ModelManifest,
    ModelRegistry,
    compute_file_sha256,
)
import numpy as np
import pandas as pd


def check_model_manifests() -> bool:
    print("[Gate 1] Validating saved model manifests and artifact checksums...")
    models_dir = ROOT / "models"
    manifest_files = list(models_dir.glob("*_manifest.json"))
    if not manifest_files:
        print("  FAIL: No model manifests found in models/")
        return False

    for mf in manifest_files:
        manifest = ModelManifest.load(mf)
        print(f"  Validating manifest: {manifest.model_id} (version {manifest.version})")
        if not manifest.artifact_path or not Path(manifest.artifact_path).is_file():
            print(f"  FAIL: Artifact path missing or not on disk: {manifest.artifact_path}")
            return False
        if manifest.artifact_checksum_sha256:
            actual_sha = compute_file_sha256(manifest.artifact_path)
            if actual_sha != manifest.artifact_checksum_sha256:
                print(f"  FAIL: Checksum mismatch for {manifest.artifact_path}")
                return False
        print(f"    OK -> {manifest.architecture}")
    return True


def check_contract_rejections() -> bool:
    print("\n[Gate 2] Verifying machine-checked contract rejection of cross-source data...")
    nasa_contract = get_nasa_contract("P-1", "SMAP", 25)
    esa_manifest_path = ROOT / "models" / "esa_lstm_CADC0872_manifest.json"
    if not esa_manifest_path.is_file():
        print("  FAIL: esa_lstm_CADC0872_manifest.json missing")
        return False

    esa_manifest = ModelManifest.load(esa_manifest_path)
    outcome, reason = ModelRegistry.validate_compatibility(esa_manifest, nasa_contract, verify_artifact_file=False)
    if outcome == CompatibilityOutcome.COMPATIBLE:
        print("  FAIL: Incompatible NASA data was improperly accepted by ESA model manifest!")
        return False
    print(f"  OK -> Incompatibility caught: {outcome.value} ({reason})")
    return True


def check_consensus_safety() -> bool:
    print("\n[Gate 3] Verifying consensus safeguards against skipped detectors...")
    stat_ev = pd.DataFrame([{"start": 10, "end": 20, "peak_score": 4.0, "severity": "medium"}])
    skipped_ev = pd.DataFrame([{"start": 12, "end": 22, "peak_score": 5.0, "severity": "high"}])

    results = {
        "Stat": DetectorRunResult("Stat", "Stat", ExecutionStatus.EXECUTED, np.ones(50), stat_ev, 3.5, "default"),
        "LSTM": DetectorRunResult("LSTM", "LSTM", ExecutionStatus.SKIPPED, np.array([]), skipped_ev, 0.0, "none"),
    }
    consensus = compute_cross_detector_consensus(results, min_agreement=2)
    if len(consensus) > 0:
        print("  FAIL: Skipped detector contributed to consensus!")
        return False
    print("  OK -> Consensus safely empty when fewer than 2 detectors successfully executed.")
    return True


def check_evaluation_invariants() -> bool:
    print("\n[Gate 4] Verifying evaluation invariant (detected = TP + FP)...")
    det_df = pd.DataFrame([
        {"start": 10, "end": 20, "peak_score": 4.0, "severity": "medium"},
        {"start": 30, "end": 40, "peak_score": 4.0, "severity": "medium"},
    ])
    gt = [(15, 25)]
    m = evaluate_event_detection(det_df, gt, 100, "Test", "Test")
    if m.detected_events_count != (m.true_positives + m.false_positives):
        print(f"  FAIL: Invariant broken: {m.detected_events_count} != {m.true_positives} + {m.false_positives}")
        return False
    print(f"  OK -> Invariant verified: {m.detected_events_count} = {m.true_positives} TP + {m.false_positives} FP")
    return True


def run_unit_test_suite() -> bool:
    print("\n[Gate 5] Running full repository unit test suite...")
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"))
    runner = unittest.TextTestRunner(verbosity=1)
    res = runner.run(suite)
    return res.wasSuccessful()


def main():
    print("=" * 70)
    print("🛰️ ORBITGUARD-AI RELEASE AND COMPATIBILITY GATE")
    print("=" * 70)

    checks = [
        check_model_manifests(),
        check_contract_rejections(),
        check_consensus_safety(),
        check_evaluation_invariants(),
        run_unit_test_suite(),
    ]

    print("\n" + "=" * 70)
    if all(checks):
        print("✅ RELEASE GATE PASSED: All contracts, manifests, and regression tests verified.")
        sys.exit(0)
    else:
        print("❌ RELEASE GATE FAILED: One or more compatibility or integrity gates failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

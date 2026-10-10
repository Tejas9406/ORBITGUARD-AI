"""Repeatable historical telemetry replay and evaluation on real ESA OPS-SAT-1 flight data.

Supports:
- Chronological batch processing of genuine ESA telemetry.
- Configurable telemetry channel selection across all 9 ADCS sensors.
- Multi-detector analysis (Statistical, Isolation Forest, LSTM compatibility check).
- Satellite health assessment per stream with evidence-based status (NORMAL, REVIEW, HIGH_PRIORITY).
- Export of detailed evaluation reports and execution history.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from backend.coordinator import OrbitGuardPipeline
from backend.esa_telemetry import ESA_OPSSAT_CHANNEL_METADATA, ESATelemetryLoader
from backend.health import ChannelHealthSummary, assess_channel_health
from backend.history import EvaluationHistory

REPORTS_DIR = ROOT / "reports"


def run_esa_historical_replay(
    channel_id: str = "CADC0872",
    max_samples: int = 5000,
    batch_size: int = 1000,
    record_history: bool = True,
):
    print("=" * 70)
    print("🛰️ ORBITGUARD-AI: REAL ESA OPS-SAT-1 TELEMETRY HISTORICAL REPLAY")
    print("=" * 70)
    print(f"Target Channel: {channel_id}")
    meta = ESA_OPSSAT_CHANNEL_METADATA.get(channel_id, {})
    print(f"Subsystem:      {meta.get('subsystem', 'Unknown')}")
    print(f"Parameter:      {meta.get('parameter', channel_id)} ({meta.get('unit', '')})")
    print(f"Description:    {meta.get('description', '')}")
    print(f"Provenance:     Zenodo 15108715 (ESA OPS-SAT-AD Benchmark)")
    print(f"Data Category:  HISTORICAL_REPLAY (Real In-Orbit Telemetry, 2022)")

    loader = ESATelemetryLoader()
    inp, gt = loader.to_canonical_input(channel_id, max_test_samples=max_samples)

    total_obs = len(inp.test_data)
    timestamps = inp.metadata.get("timestamps", [])
    print(f"Loaded {total_obs:,} test observations.")
    if timestamps:
        print(f"Time Range:     {timestamps[0]} -> {timestamps[-1]}")
    print(f"Ground Truth Reference Events: {len(gt)}")

    pipeline = OrbitGuardPipeline()

    print("\n--- Phase 1: End-to-End Pipeline Evaluation ---")
    t0 = time.time()
    result = pipeline.run(
        inp,
        ground_truth_ranges=gt,
        enable_lstm=True,  # Will transparently report Skipped (Incompatible dimensions)
        enable_isolation_forest=True,
        calibrate_thresholds=True,
        record_history=record_history,
    )
    elapsed = time.time() - t0

    print(f"Pipeline executed in {elapsed:.2f} seconds.")
    print("\n[Comparative Detector Benchmarking]")
    comp_df = result.comparative_summary[
        [
            "detector_name",
            "status",
            "total_observations",
            "ground_truth_events_count",
            "detected_events_count",
            "true_positives",
            "false_positives",
            "false_negatives",
            "precision",
            "recall",
            "f1_score",
            "execution_time_seconds",
        ]
    ]
    print(comp_df.to_string(index=False))

    # Health Assessment
    print("\n--- Phase 2: Evidence-Based Spacecraft Health Assessment ---")
    stat_res = result.detector_results.get("Statistical Baseline")
    iso_res = result.detector_results.get("Isolation Forest")

    iso_tp = iso_res.metrics.true_positives if iso_res and iso_res.metrics else 0
    iso_fp = iso_res.metrics.false_positives if iso_res and iso_res.metrics else 0
    iso_fn = iso_res.metrics.false_negatives if iso_res and iso_res.metrics else 0
    iso_det = len(iso_res.events) if iso_res else 0

    health_row = pd.Series({
        "chan_id": f"ESA_{channel_id}",
        "spacecraft": "OPS-SAT-1",
        "true_positives": iso_tp,
        "false_positives": iso_fp,
        "false_negatives": iso_fn,
        "n_predicted_anoms": iso_det,
        "num_true_anoms": len(gt),
    })
    health_assessment = assess_channel_health(health_row)
    # Customize explanation with verified physical context
    status_color = "🔴" if health_assessment.status == "High Priority" else "🟡" if health_assessment.status == "Review" else "🟢"
    print(f"Operational Health Status: {status_color} {health_assessment.status.upper()}")
    print(f"Subsystem Assignment:      {meta.get('subsystem', 'ADCS')}")
    print(f"Primary Sensor:            {meta.get('parameter', channel_id)} in {meta.get('unit', '')}")
    print(f"Diagnostic Justification:  {health_assessment.explanation}")
    print(f"Consensus Incidents Count: {len(result.consensus_events)}")

    # Chronological Batch Replay Demonstration
    print(f"\n--- Phase 3: Chronological Stream Replay (Batches of {batch_size} samples) ---")
    n_batches = int(np.ceil(total_obs / batch_size))
    for b_idx in range(n_batches):
        b_start = b_idx * batch_size
        b_end = min(total_obs, (b_idx + 1) * batch_size)
        slice_vals = inp.test_data[b_start:b_end]
        t_start_str = timestamps[b_start] if timestamps else f"step {b_start}"
        t_end_str = timestamps[b_end - 1] if timestamps else f"step {b_end - 1}"
        
        # Check anomalies in this batch
        batch_gt = [(s, e) for s, e in gt if max(s, b_start) <= min(e, b_end)]
        iso_events_in_b = [
            row for _, row in iso_res.events.iterrows()
            if max(int(row["start"]), b_start) <= min(int(row["end"]), b_end)
        ] if iso_res is not None and not iso_res.events.empty else []

        print(
            f"  [Batch {b_idx + 1}/{n_batches}] [{t_start_str} -> {t_end_str}] "
            f"Obs: {len(slice_vals):4d} | Mean={slice_vals.mean():+.5f} | "
            f"GT Events: {len(batch_gt)} | Detected Alerts: {len(iso_events_in_b)}"
        )

    return result, health_assessment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OrbitGuard AI on real ESA OPS-SAT-1 flight telemetry.")
    parser.add_argument("--channel", type=str, default="CADC0872", help="ESA CADC channel ID")
    parser.add_argument("--max_samples", type=int, default=3000, help="Max test samples to evaluate")
    parser.add_argument("--batch_size", type=int, default=1000, help="Replay batch size")
    args = parser.parse_args()

    run_esa_historical_replay(
        channel_id=args.channel,
        max_samples=args.max_samples,
        batch_size=args.batch_size,
    )

"""Traceable anomaly-event evidence records."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .ingestion import TelemetryInput


def _iso_or_index(timestamps: Optional[List[str]], index: int, kind: str) -> Dict[str, Any]:
    if timestamps and 0 <= index < len(timestamps) and timestamps[index] is not None and kind == "utc":
        return {"timestamp": timestamps[index], "timestamp_kind": "utc", "observation_index": index}
    return {"timestamp": None, "timestamp_kind": "index", "observation_index": index, "index_label": f"t+{index}"}


def attach_event_evidence(
    events: pd.DataFrame,
    telemetry: TelemetryInput,
    scores: np.ndarray,
    threshold: float,
    detector_name: str,
    detector_version: str,
    execution_status: str,
    dataset_id: str,
    model_id: Optional[str] = None,
) -> pd.DataFrame:
    if events is None or events.empty:
        return events
    signal = np.asarray(telemetry.target_signal, dtype=np.float64)
    timestamps = telemetry.timestamps
    rows = []
    for _, ev in events.iterrows():
        start = int(ev["start"])
        end = int(ev["end"])
        start = max(0, min(start, len(signal) - 1)) if len(signal) else 0
        end = max(start, min(end, len(signal) - 1)) if len(signal) else 0
        window = signal[start : end + 1] if len(signal) else np.array([])
        # Historical baseline: observations before the event, not including the flagged window.
        baseline_src = signal[:start] if start > 10 else signal
        baseline_median = float(np.median(baseline_src)) if len(baseline_src) else None
        baseline_mad = float(np.median(np.abs(baseline_src - baseline_median))) if baseline_median is not None else None
        peak_idx_local = int(np.argmax(np.abs(window - (baseline_median or 0)))) if len(window) else 0
        peak_idx = start + peak_idx_local
        observed = float(signal[peak_idx]) if len(signal) else None
        deviation = None if observed is None or baseline_median is None else float(observed - baseline_median)
        score = float(ev.get("peak_score", 0.0))
        start_t = _iso_or_index(timestamps, start, telemetry.timestamp_kind)
        end_t = _iso_or_index(timestamps, end, telemetry.timestamp_kind)
        rows.append(
            {
                **ev.to_dict(),
                "event_id": f"{dataset_id}:{telemetry.channel_id}:{detector_name}:{start}-{end}",
                "dataset_id": dataset_id,
                "provenance": telemetry.provenance.value if hasattr(telemetry.provenance, "value") else str(telemetry.provenance),
                "channel_id": telemetry.channel_id,
                "units": telemetry.units,
                "physical_meaning": telemetry.physical_meaning,
                "detector_name": detector_name,
                "detector_version": detector_version,
                "model_id": model_id,
                "execution_status": execution_status,
                "threshold": threshold,
                "observed_value": observed,
                "baseline_median": baseline_median,
                "baseline_mad": baseline_mad,
                "deviation": deviation,
                "window_mean": float(np.mean(window)) if len(window) else None,
                "window_min": float(np.min(window)) if len(window) else None,
                "window_max": float(np.max(window)) if len(window) else None,
                "start_timestamp": start_t["timestamp"],
                "end_timestamp": end_t["timestamp"],
                "timestamp_kind": start_t["timestamp_kind"],
                "claim": "unusual_telemetry_pattern",
                "claim_note": (
                    "Detector flagged an unusual pattern. This is not a confirmed physical fault."
                ),
            }
        )
    return pd.DataFrame(rows)

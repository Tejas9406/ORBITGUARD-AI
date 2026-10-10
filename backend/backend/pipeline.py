"""Generate detector-ready feature tables and baseline anomaly events."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data import TelemetryDataset
from .events import group_events
from .features import build_features


def process_dataset(root: str | Path, output_dir: str | Path, window: int = 100, threshold: float = 3.5) -> dict:
    """Process safely labelled channels into parquet feature tables and a manifest."""
    dataset = TelemetryDataset(root)
    audit = dataset.audit()
    destination = Path(output_dir)
    channels_dir = destination / "channels"
    channels_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for channel_id in dataset.channel_ids():
        channel = dataset.load_channel(channel_id)
        features = build_features(channel.target_test, window=window)
        events = group_events(features["robust_zscore"].to_numpy(), threshold=threshold)
        features.to_parquet(channels_dir / f"{channel_id}.parquet", index=False)
        events.to_csv(channels_dir / f"{channel_id}.events.csv", index=False)
        summaries.append({
            "channel_id": channel_id,
            "spacecraft": channel.metadata.spacecraft,
            "test_observations": int(len(channel.target_test)),
            "feature_width": int(channel.test.shape[1]),
            "known_anomaly_ranges": channel.metadata.anomaly_ranges,
            "baseline_event_count": int(len(events)),
        })
    manifest = {"audit": audit.to_dict(), "parameters": {"window": window, "threshold": threshold, "detector": "causal robust rolling Z-score"}, "channels": summaries}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pd.DataFrame(summaries).to_csv(destination / "channel_summary.csv", index=False)
    return manifest

"""Adapter for Real ESA OPS-SAT Flight Telemetry.

Ingests genuine historical telemetry from the ESA OPS-SAT-AD benchmark
(Zenodo 15108715 / ESA OPS-SAT-1 spacecraft).

Preserves:
- Original timestamps, channel IDs, documented units, and provenance.
- Clear separation between training partitions (train=1) and test partitions (train=0).
- Ground truth anomaly intervals extracted from expert annotations.
- Explicit mapping to OrbitGuard AI canonical TelemetryInput (SourceType.HISTORICAL_REPLAY).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .ingestion import SourceType, TelemetryInput, ValidationStatus, validate_and_prepare

logger = logging.getLogger("orbitguard.esa")

DEFAULT_SEGMENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "external" / "esa_opssat" / "segments.csv"

# Verified ESA Telemetry Dictionary for OPS-SAT ADCS CADC mnemonics
ESA_OPSSAT_CHANNEL_METADATA: Dict[str, Dict[str, str]] = {
    "CADC0872": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Gyro Angular Velocity X",
        "unit": "rad/s",
        "description": "3-axis rate gyro measured angular rotation rate around body X-axis",
    },
    "CADC0873": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Gyro Angular Velocity Y",
        "unit": "rad/s",
        "description": "3-axis rate gyro measured angular rotation rate around body Y-axis",
    },
    "CADC0874": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Gyro Angular Velocity Z",
        "unit": "rad/s",
        "description": "3-axis rate gyro measured angular rotation rate around body Z-axis",
    },
    "CADC0884": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Sun Sensor Angle X",
        "unit": "rad",
        "description": "Coarse sun sensor incidence angle X",
    },
    "CADC0886": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Sun Sensor Angle Error",
        "unit": "rad",
        "description": "Coarse sun sensor tracking error deviation",
    },
    "CADC0888": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Magnetometer Estimated Field",
        "unit": "T (Tesla)",
        "description": "3-axis fluxgate magnetometer total magnetic flux density",
    },
    "CADC0890": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Star Tracker Residual Error",
        "unit": "rad",
        "description": "Optical star tracker attitude determination residual angular error",
    },
    "CADC0892": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Fine Sun Sensor Elevation",
        "unit": "rad",
        "description": "Fine sun sensor pitch/elevation angle relative to boresight",
    },
    "CADC0894": {
        "subsystem": "ADCS (Attitude Determination & Control)",
        "parameter": "Fine Sun Sensor Azimuth",
        "unit": "rad",
        "description": "Fine sun sensor yaw/azimuth angle relative to boresight",
    },
}


@dataclass
class ESATelemetryChannel:
    channel_id: str
    metadata: Dict[str, str]
    train_data: np.ndarray
    test_data: np.ndarray
    train_timestamps: List[str]
    test_timestamps: List[str]
    test_ground_truth_ranges: List[Tuple[int, int]]
    total_samples: int
    train_samples: int
    test_samples: int
    test_anomalous_samples: int


class ESATelemetryLoader:
    """Loads and prepares ESA OPS-SAT flight telemetry."""

    def __init__(self, segments_csv_path: Optional[str | Path] = None):
        self.path = Path(segments_csv_path) if segments_csv_path else DEFAULT_SEGMENTS_PATH
        if not self.path.is_file():
            raise FileNotFoundError(f"ESA segments.csv not found at: {self.path}")

    def list_channels(self) -> List[str]:
        """List all unique channels in the dataset."""
        df = pd.read_csv(self.path, usecols=["channel"])
        return sorted(df["channel"].unique().tolist())

    def load_channel(
        self,
        channel_id: str,
        max_test_samples: Optional[int] = None,
    ) -> ESATelemetryChannel:
        """Load a specific ESA telemetry channel with train/test partitioning."""
        df = pd.read_csv(self.path)
        sub = df[df["channel"] == channel_id].copy()
        if sub.empty:
            raise ValueError(f"Channel {channel_id} not found in ESA dataset.")

        # Ensure chronological ordering
        sub["dt"] = pd.to_datetime(sub["timestamp"])
        sub = sub.sort_values("dt").reset_index(drop=True)

        train_mask = sub["train"] == 1
        test_mask = sub["train"] == 0

        train_sub = sub[train_mask].reset_index(drop=True)
        test_sub = sub[test_mask].reset_index(drop=True)

        if max_test_samples is not None and len(test_sub) > max_test_samples:
            test_sub = test_sub.iloc[:max_test_samples].copy()

        train_vals = train_sub["value"].to_numpy(dtype=np.float64)
        test_vals = test_sub["value"].to_numpy(dtype=np.float64)

        train_times = train_sub["timestamp"].tolist()
        test_times = test_sub["timestamp"].tolist()

        # Extract contiguous ground truth anomaly index ranges in test partition
        test_anom_mask = test_sub["anomaly"].to_numpy() == 1
        gt_ranges = []
        in_anom = False
        start_idx = 0
        for i, is_anom in enumerate(test_anom_mask):
            if is_anom and not in_anom:
                in_anom = True
                start_idx = i
            elif not is_anom and in_anom:
                in_anom = False
                gt_ranges.append((start_idx, i - 1))
        if in_anom:
            gt_ranges.append((start_idx, len(test_anom_mask) - 1))

        meta = ESA_OPSSAT_CHANNEL_METADATA.get(
            channel_id,
            {
                "subsystem": "UNKNOWN / UNMAPPED",
                "parameter": channel_id,
                "unit": "unknown",
                "description": f"ESA Telemetry Mnemonic {channel_id}",
            },
        )

        return ESATelemetryChannel(
            channel_id=channel_id,
            metadata=meta,
            train_data=train_vals,
            test_data=test_vals,
            train_timestamps=train_times,
            test_timestamps=test_times,
            test_ground_truth_ranges=gt_ranges,
            total_samples=len(sub),
            train_samples=len(train_vals),
            test_samples=len(test_vals),
            test_anomalous_samples=int(test_anom_mask.sum()),
        )

    def to_canonical_input(
        self,
        channel_id: str,
        max_test_samples: Optional[int] = None,
    ) -> Tuple[TelemetryInput, List[Tuple[int, int]]]:
        """Convert ESA channel to canonical OrbitGuard TelemetryInput."""
        ch = self.load_channel(channel_id, max_test_samples=max_test_samples)

        # Build TelemetryInput
        inp = validate_and_prepare(
            ch.test_data,
            source_type=SourceType.HISTORICAL_REPLAY,
            channel_id=f"ESA_OPSSAT_{channel_id}",
            train_data=ch.train_data,
        )

        inp.metadata = {
            "source_type": "HISTORICAL_REPLAY",
            "satellite_name": "OPS-SAT-1",
            "mission": "ESA OPS-SAT Spacecraft Operations",
            "norad_id": 44878,
            "channel_id": ch.channel_id,
            "subsystem": ch.metadata["subsystem"],
            "parameter": ch.metadata["parameter"],
            "unit": ch.metadata["unit"],
            "description": ch.metadata["description"],
            "timestamps": ch.test_timestamps,
            "provenance": "Zenodo 15108715 (ESA OPS-SAT-AD Benchmark)",
            "train_samples": ch.train_samples,
            "test_samples": ch.test_samples,
        }

        return inp, ch.test_ground_truth_ranges

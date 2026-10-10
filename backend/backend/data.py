"""Load and audit local Telemanom data without relying on legacy Keras code."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


def parse_ranges(value: object) -> list[tuple[int, int]]:
    """Parse a Telemanom CSV range field into inclusive (start, end) tuples."""
    return [(int(start), int(end)) for start, end in ast.literal_eval(str(value))]


def parse_classes(value: object) -> list[str]:
    """Parse values such as ``[point, contextual]`` with unquoted tokens."""
    return [item.strip() for item in str(value).strip().strip("[]").split(",") if item.strip()]


@dataclass(frozen=True)
class ChannelMetadata:
    channel_id: str
    spacecraft: str
    anomaly_ranges: list[tuple[int, int]]
    anomaly_classes: list[str]
    declared_values: int


@dataclass(frozen=True)
class ChannelData:
    metadata: ChannelMetadata | None
    train: np.ndarray
    test: np.ndarray

    @property
    def target_train(self) -> np.ndarray:
        return self.train[:, 0]

    @property
    def target_test(self) -> np.ndarray:
        return self.test[:, 0]


@dataclass(frozen=True)
class DatasetAudit:
    raw_channel_count: int
    label_row_count: int
    unambiguous_labelled_channel_count: int
    feature_widths: dict[int, int]
    duplicate_label_channels: dict[str, int]
    conflicting_label_channels: list[str]
    unlabelled_raw_channels: list[str]
    labelled_channels_missing_raw_data: list[str]
    shape_mismatches: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class TelemetryDataset:
    """Access train/test telemetry while enforcing safe label-quality rules."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.train_dir = self.root / "data" / "train"
        self.test_dir = self.root / "data" / "test"
        self.labels_path = self.root / "labeled_anomalies.csv"
        self._labels = self._read_labels()

    def _read_labels(self) -> pd.DataFrame:
        labels = pd.read_csv(self.labels_path)
        labels["ranges"] = labels["anomaly_sequences"].map(parse_ranges)
        labels["classes"] = labels["class"].map(parse_classes)
        return labels

    def _raw_channel_ids(self) -> set[str]:
        return {path.stem for path in self.test_dir.glob("*.npy")}

    def audit(self) -> DatasetAudit:
        raw_ids = self._raw_channel_ids()
        label_counts = self._labels.groupby("chan_id").size()
        duplicates = {channel: int(count) for channel, count in label_counts.items() if count > 1}
        conflicts = []
        for channel in duplicates:
            rows = self._labels[self._labels["chan_id"] == channel]
            if rows["anomaly_sequences"].nunique() > 1 or rows["class"].nunique() > 1:
                conflicts.append(channel)

        labelled_ids = set(self._labels["chan_id"])
        widths: dict[int, int] = {}
        mismatches: list[str] = []
        for channel in sorted(raw_ids):
            train_path = self.train_dir / f"{channel}.npy"
            test_path = self.test_dir / f"{channel}.npy"
            if not train_path.exists():
                mismatches.append(f"{channel}: missing train array")
                continue
            train, test = np.load(train_path, mmap_mode="r"), np.load(test_path, mmap_mode="r")
            widths[int(test.shape[1])] = widths.get(int(test.shape[1]), 0) + 1
            if train.ndim != 2 or test.ndim != 2 or train.shape[1] != test.shape[1]:
                mismatches.append(f"{channel}: incompatible train/test shapes {train.shape} / {test.shape}")

        return DatasetAudit(
            raw_channel_count=len(raw_ids),
            label_row_count=len(self._labels),
            unambiguous_labelled_channel_count=len((labelled_ids & raw_ids) - set(conflicts)),
            feature_widths=widths,
            duplicate_label_channels=duplicates,
            conflicting_label_channels=sorted(conflicts),
            unlabelled_raw_channels=sorted(raw_ids - labelled_ids),
            labelled_channels_missing_raw_data=sorted(labelled_ids - raw_ids),
            shape_mismatches=mismatches,
        )

    def channel_ids(self, labelled_only: bool = True, include_conflicts: bool = False) -> list[str]:
        raw_ids = self._raw_channel_ids()
        if not labelled_only:
            return sorted(raw_ids)
        ids = raw_ids & set(self._labels["chan_id"])
        if not include_conflicts:
            ids -= set(self.audit().conflicting_label_channels)
        return sorted(ids)

    def metadata_for(self, channel_id: str) -> ChannelMetadata | None:
        rows = self._labels[self._labels["chan_id"] == channel_id]
        if rows.empty:
            return None
        if len(rows) > 1 and not rows["anomaly_sequences"].eq(rows.iloc[0]["anomaly_sequences"]).all():
            raise ValueError(f"{channel_id} has conflicting labels and cannot be evaluated safely")
        row = rows.iloc[0]
        return ChannelMetadata(channel_id, str(row["spacecraft"]), list(row["ranges"]), list(row["classes"]), int(row["num_values"]))

    def load_channel(self, channel_id: str, labelled_only: bool = True) -> ChannelData:
        if channel_id not in self._raw_channel_ids():
            raise FileNotFoundError(f"No raw telemetry found for {channel_id}")
        metadata = self.metadata_for(channel_id)
        if labelled_only and metadata is None:
            raise ValueError(f"{channel_id} is unlabelled and cannot be used for supervised evaluation")
        train = np.load(self.train_dir / f"{channel_id}.npy").astype(np.float64)
        test = np.load(self.test_dir / f"{channel_id}.npy").astype(np.float64)
        if train.ndim != 2 or test.ndim != 2 or train.shape[1] != test.shape[1]:
            raise ValueError(f"{channel_id} has incompatible train/test feature shapes")
        return ChannelData(metadata, train, test)

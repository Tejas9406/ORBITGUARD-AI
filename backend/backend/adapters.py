"""Source-agnostic dataset adapters for OrbitGuard AI.

Adding a telemetry source should mean implementing DatasetAdapter and registering
it. Detectors, evaluation, health, and the frontend consume the canonical form
produced here rather than source-specific layouts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .contracts import TelemetryContract, contract_from_telemetry_input, get_esa_opssat_contract, get_nasa_contract
from .data import TelemetryDataset
from .esa_telemetry import ESA_OPSSAT_CHANNEL_METADATA, ESATelemetryLoader
from .ingestion import (
    ProvenanceKind,
    SourceType,
    TelemetryInput,
    ingest_csv,
    ingest_nasa_channel,
    validate_and_prepare,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ChannelDescriptor:
    channel_id: str
    display_name: str
    units: str
    physical_meaning: str
    subsystem: str
    feature_dim: int
    n_observations: Optional[int] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    timestamp_kind: str = "index"
    labels_available: bool = False


@dataclass
class DatasetDescriptor:
    dataset_id: str
    name: str
    source: str
    satellite_name: str
    provenance: str
    licence: str
    description: str
    available: bool
    unavailable_reason: Optional[str] = None
    live: bool = False
    simulated: bool = False


@dataclass
class AdapterLoadResult:
    telemetry: TelemetryInput
    contract: TelemetryContract
    ground_truth_ranges: List[Tuple[int, int]]
    channel: ChannelDescriptor
    dataset: DatasetDescriptor
    extras: Dict[str, Any] = field(default_factory=dict)


class DatasetAdapter(ABC):
    dataset_id: str

    @abstractmethod
    def describe(self) -> DatasetDescriptor:
        ...

    @abstractmethod
    def list_channels(self) -> List[ChannelDescriptor]:
        ...

    @abstractmethod
    def load_channel(
        self,
        channel_id: str,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        max_points: Optional[int] = None,
    ) -> AdapterLoadResult:
        ...


class NASATelemanomAdapter(DatasetAdapter):
    dataset_id = "nasa_smap_msl"

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else REPO_ROOT
        self.test_dir = self.root / "data" / "test"
        self.train_dir = self.root / "data" / "train"
        self.labels_path = self.root / "labeled_anomalies.csv"

    def describe(self) -> DatasetDescriptor:
        available = self.test_dir.is_dir() and any(self.test_dir.glob("*.npy"))
        return DatasetDescriptor(
            dataset_id=self.dataset_id,
            name="NASA SMAP/MSL Telemanom Benchmark",
            source="NASA_SMAP_MSL",
            satellite_name="SMAP / MSL",
            provenance=ProvenanceKind.HISTORICAL_REAL.value,
            licence="Research benchmark (Hundman et al. 2018); anonymized channels",
            description=(
                "Historical NASA SMAP and MSL telemetry benchmark. Channel IDs and "
                "values are anonymized. Not a live spacecraft feed."
            ),
            available=available,
            unavailable_reason=None if available else "NASA train/test .npy files are not present on disk.",
            live=False,
            simulated=False,
        )

    def list_channels(self) -> List[ChannelDescriptor]:
        if not self.test_dir.is_dir():
            return []
        labels: Dict[str, Any] = {}
        if self.labels_path.is_file():
            df = pd.read_csv(self.labels_path)
            for _, row in df.drop_duplicates(subset=["chan_id"]).iterrows():
                labels[str(row["chan_id"])] = row
        channels = []
        for path in sorted(self.test_dir.glob("*.npy")):
            cid = path.stem
            row = labels.get(cid)
            n_obs = int(row["num_values"]) if row is not None else None
            channels.append(
                ChannelDescriptor(
                    channel_id=cid,
                    display_name=cid,
                    units="normalized_ratio",
                    physical_meaning="Unknown / unmapped (anonymized NASA Telemanom channel)",
                    subsystem="Unknown / unmapped",
                    feature_dim=0,
                    n_observations=n_obs,
                    timestamp_kind="index",
                    labels_available=row is not None,
                )
            )
        return channels

    def load_channel(
        self,
        channel_id: str,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        max_points: Optional[int] = None,
    ) -> AdapterLoadResult:
        _ = (time_start, time_end)
        desc = self.describe()
        if not desc.available:
            raise FileNotFoundError(desc.unavailable_reason or "NASA data unavailable")
        dataset = TelemetryDataset(self.root)
        channel = dataset.load_channel(channel_id)
        spacecraft = channel.metadata.spacecraft if channel.metadata else "unknown"
        test = channel.test
        if max_points is not None:
            test = test[: int(max_points)]
        telemetry = validate_and_prepare(
            test,
            source_type=SourceType.NASA_NPY,
            channel_id=channel_id,
            train_data=channel.train,
            source_dataset="NASA_SMAP_MSL",
            satellite_name=spacecraft,
            provenance=ProvenanceKind.HISTORICAL_REAL,
            timestamp_kind="index",
            units="normalized_ratio",
            physical_meaning="Unknown / unmapped (anonymized NASA Telemanom channel)",
        )
        telemetry.metadata["spacecraft"] = spacecraft
        dim = int(telemetry.feature_dim)
        contract = get_nasa_contract(channel_id, spacecraft, dim)
        gt = list(channel.metadata.anomaly_ranges) if channel.metadata else []
        if max_points is not None:
            gt = [(s, min(e, int(max_points) - 1)) for s, e in gt if s < int(max_points)]
        ch_desc = ChannelDescriptor(
            channel_id=channel_id,
            display_name=channel_id,
            units="normalized_ratio",
            physical_meaning="Unknown / unmapped (anonymized NASA Telemanom channel)",
            subsystem="Unknown / unmapped",
            feature_dim=dim,
            n_observations=len(telemetry.target_signal),
            timestamp_kind="index",
            labels_available=bool(gt),
        )
        return AdapterLoadResult(telemetry, contract, gt, ch_desc, desc)


class ESAOpsSatAdapter(DatasetAdapter):
    dataset_id = "esa_ops_sat_ad"

    def __init__(self, segments_path: Optional[Path] = None):
        self.segments_path = Path(segments_path) if segments_path else (
            REPO_ROOT / "data" / "external" / "esa_opssat" / "segments.csv"
        )

    def describe(self) -> DatasetDescriptor:
        available = self.segments_path.is_file()
        return DatasetDescriptor(
            dataset_id=self.dataset_id,
            name="ESA OPS-SAT-AD Historical Telemetry",
            source="ESA_OPS_SAT_AD",
            satellite_name="OPS-SAT-1",
            provenance=ProvenanceKind.HISTORICAL_REAL.value,
            licence="Zenodo 15108715",
            description=(
                "Historical ESA OPS-SAT attitude-control telemetry with expert anomaly "
                "segments. This is archived benchmark data, not a live engineering feed."
            ),
            available=available,
            unavailable_reason=None if available else "ESA segments.csv is not present on disk.",
            live=False,
            simulated=False,
        )

    def list_channels(self) -> List[ChannelDescriptor]:
        if not self.segments_path.is_file():
            return []
        loader = ESATelemetryLoader(self.segments_path)
        channels = []
        for cid in loader.list_channels():
            meta = ESA_OPSSAT_CHANNEL_METADATA.get(
                cid,
                {
                    "subsystem": "Unknown / unmapped",
                    "parameter": cid,
                    "unit": "unspecified",
                    "description": f"ESA telemetry mnemonic {cid}",
                },
            )
            channels.append(
                ChannelDescriptor(
                    channel_id=cid,
                    display_name=meta["parameter"],
                    units=meta["unit"],
                    physical_meaning=meta["description"],
                    subsystem=meta["subsystem"],
                    feature_dim=1,
                    timestamp_kind="utc",
                    labels_available=True,
                )
            )
        return channels

    def load_channel(
        self,
        channel_id: str,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        max_points: Optional[int] = None,
    ) -> AdapterLoadResult:
        loader = ESATelemetryLoader(self.segments_path)
        ch = loader.load_channel(channel_id, max_test_samples=max_points)
        test_times = list(ch.test_timestamps)
        train_times = list(ch.train_timestamps)
        test_vals = ch.test_data
        gt = list(ch.test_ground_truth_ranges)

        if time_start or time_end:
            ts = pd.to_datetime(test_times, utc=True, errors="coerce")
            mask = np.ones(len(ts), dtype=bool)
            if time_start:
                mask &= ts >= pd.to_datetime(time_start, utc=True)
            if time_end:
                mask &= ts <= pd.to_datetime(time_end, utc=True)
            idx = np.flatnonzero(mask)
            if len(idx) == 0:
                raise ValueError("Selected time range contains no observations for this channel.")
            test_vals = test_vals[idx]
            test_times = [test_times[i] for i in idx]
            # Ground-truth ranges are index-based on the original test window; remap if filtered from start.
            if idx[0] != 0 or len(idx) != len(ch.test_data):
                shifted = []
                offset = int(idx[0])
                kept = set(idx.tolist())
                for s, e in gt:
                    overlap = [i for i in range(s, e + 1) if i in kept]
                    if overlap:
                        shifted.append((overlap[0] - offset, overlap[-1] - offset))
                gt = shifted

        telemetry = validate_and_prepare(
            test_vals,
            source_type=SourceType.HISTORICAL_REPLAY,
            channel_id=f"ESA_OPSSAT_{channel_id}",
            train_data=ch.train_data,
            source_dataset="ESA_OPS_SAT_AD",
            satellite_name="OPS-SAT-1",
            provenance=ProvenanceKind.HISTORICAL_REAL,
            timestamps=test_times,
            timestamp_kind="utc",
            units=ch.metadata.get("unit", "unspecified"),
            physical_meaning=ch.metadata.get("description", "Unknown / unmapped"),
            feature_names=[f"OPS_SAT_{channel_id}"],
        )
        telemetry.metadata.update(
            {
                "source_type": "HISTORICAL_REPLAY",
                "satellite_name": "OPS-SAT-1",
                "channel_id": channel_id,
                "subsystem": ch.metadata.get("subsystem", "Unknown / unmapped"),
                "parameter": ch.metadata.get("parameter", channel_id),
                "unit": ch.metadata.get("unit", "unspecified"),
                "description": ch.metadata.get("description", ""),
                "timestamps": test_times,
                "train_timestamps_count": len(train_times),
                "provenance": "Zenodo 15108715 (ESA OPS-SAT-AD Benchmark)",
                "live": False,
            }
        )
        contract = get_esa_opssat_contract(channel_id)
        ch_desc = ChannelDescriptor(
            channel_id=channel_id,
            display_name=ch.metadata.get("parameter", channel_id),
            units=ch.metadata.get("unit", "unspecified"),
            physical_meaning=ch.metadata.get("description", "Unknown / unmapped"),
            subsystem=ch.metadata.get("subsystem", "Unknown / unmapped"),
            feature_dim=1,
            n_observations=len(telemetry.target_signal),
            time_start=test_times[0] if test_times else None,
            time_end=test_times[-1] if test_times else None,
            timestamp_kind="utc",
            labels_available=bool(gt),
        )
        return AdapterLoadResult(telemetry, contract, gt, ch_desc, self.describe())


class GenericCSVAdapter(DatasetAdapter):
    dataset_id = "user_csv"

    def __init__(self):
        self._uploads: Dict[str, Dict[str, Any]] = {}

    def describe(self) -> DatasetDescriptor:
        return DatasetDescriptor(
            dataset_id=self.dataset_id,
            name="User-uploaded CSV telemetry",
            source="CUSTOM_UPLOAD",
            satellite_name="user_upload",
            provenance=ProvenanceKind.USER_UPLOAD.value,
            licence="Provided by the operator; provenance unknown unless declared",
            description=(
                "Tabular time series mapped by the user. Compatible statistical and "
                "unsupervised detectors may run. NASA/ESA sequence models are not used "
                "unless an explicit matching trained artifact exists."
            ),
            available=True,
            live=False,
            simulated=False,
        )

    def list_channels(self) -> List[ChannelDescriptor]:
        out = []
        for key, rec in self._uploads.items():
            out.append(
                ChannelDescriptor(
                    channel_id=key,
                    display_name=rec.get("display_name", key),
                    units=rec.get("units", "unspecified"),
                    physical_meaning=rec.get("physical_meaning", "Unknown / unmapped"),
                    subsystem="Unknown / unmapped",
                    feature_dim=rec.get("feature_dim", 1),
                    n_observations=rec.get("n_observations"),
                    timestamp_kind=rec.get("timestamp_kind", "index"),
                    labels_available=False,
                )
            )
        return out

    def register_upload(
        self,
        upload_id: str,
        path: Path,
        mapping: Dict[str, Any],
    ) -> ChannelDescriptor:
        telemetry = ingest_csv(
            path,
            telemetry_column=mapping.get("value_column"),
            timestamp_column=mapping.get("timestamp_column"),
            channel_id=mapping.get("channel_id") or upload_id,
            feature_columns=mapping.get("feature_columns"),
            units=mapping.get("units") or "unspecified",
            physical_meaning=mapping.get("physical_meaning") or "Unknown / unmapped",
            satellite_name=mapping.get("satellite_name") or "user_upload",
        )
        self._uploads[upload_id] = {
            "path": path,
            "mapping": mapping,
            "telemetry": telemetry,
            "display_name": telemetry.channel_id,
            "units": telemetry.units,
            "physical_meaning": telemetry.physical_meaning,
            "feature_dim": telemetry.feature_dim,
            "n_observations": len(telemetry.target_signal),
            "timestamp_kind": telemetry.timestamp_kind,
        }
        return ChannelDescriptor(
            channel_id=upload_id,
            display_name=telemetry.channel_id,
            units=telemetry.units,
            physical_meaning=telemetry.physical_meaning,
            subsystem="Unknown / unmapped",
            feature_dim=telemetry.feature_dim,
            n_observations=len(telemetry.target_signal),
            timestamp_kind=telemetry.timestamp_kind,
            labels_available=False,
        )

    def load_channel(
        self,
        channel_id: str,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        max_points: Optional[int] = None,
    ) -> AdapterLoadResult:
        rec = self._uploads.get(channel_id)
        if rec is None:
            raise KeyError(f"No uploaded CSV registered as '{channel_id}'.")
        telemetry: TelemetryInput = rec["telemetry"]
        if max_points is not None and len(telemetry.target_signal) > max_points:
            sliced = telemetry.target_signal[:max_points]
            train = telemetry.train_data
            telemetry = validate_and_prepare(
                sliced,
                source_type=SourceType.CSV_UPLOAD,
                channel_id=telemetry.channel_id,
                train_data=train,
                source_dataset="CUSTOM_UPLOAD",
                satellite_name=telemetry.satellite_name,
                provenance=ProvenanceKind.USER_UPLOAD,
                timestamps=(telemetry.timestamps or [])[:max_points] if telemetry.timestamps else None,
                timestamp_kind=telemetry.timestamp_kind,
                units=telemetry.units,
                physical_meaning=telemetry.physical_meaning,
                feature_names=telemetry.feature_names,
            )
        contract = contract_from_telemetry_input(telemetry)
        ch_desc = ChannelDescriptor(
            channel_id=channel_id,
            display_name=telemetry.channel_id,
            units=telemetry.units,
            physical_meaning=telemetry.physical_meaning,
            subsystem="Unknown / unmapped",
            feature_dim=telemetry.feature_dim,
            n_observations=len(telemetry.target_signal),
            timestamp_kind=telemetry.timestamp_kind,
            labels_available=False,
        )
        return AdapterLoadResult(telemetry, contract, [], ch_desc, self.describe())


class SimulatedDemoAdapter(DatasetAdapter):
    """Explicitly labelled simulated orbital telemetry. Never mixed into historical sources."""

    dataset_id = "simulated_leo_demo"

    def describe(self) -> DatasetDescriptor:
        return DatasetDescriptor(
            dataset_id=self.dataset_id,
            name="Simulated LEO orbital telemetry (labelled demo)",
            source="SIMULATED",
            satellite_name="SIM-LEO-1",
            provenance=ProvenanceKind.SIMULATED.value,
            licence="Synthetic; not flight data",
            description="Physically motivated simulation with an injected undervoltage event. Isolated from historical NASA/ESA records.",
            available=True,
            live=False,
            simulated=True,
        )

    def list_channels(self) -> List[ChannelDescriptor]:
        return [
            ChannelDescriptor(
                channel_id="bus_voltage",
                display_name="Simulated solar-array bus voltage",
                units="V",
                physical_meaning="Simulated regulated bus voltage with eclipse cycle",
                subsystem="EPS (simulated)",
                feature_dim=1,
                timestamp_kind="index",
                labels_available=True,
            )
        ]

    def load_channel(
        self,
        channel_id: str,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        max_points: Optional[int] = None,
    ) -> AdapterLoadResult:
        from .real_world import RealWorldTelemetryClient

        if channel_id != "bus_voltage":
            raise KeyError(f"Unknown simulated channel '{channel_id}'.")
        n = max_points or 1500
        client = RealWorldTelemetryClient()
        telemetry, gt = client.generate_physically_grounded_telemetry(n_samples=n)
        telemetry.source_dataset = "SIMULATED"
        telemetry.provenance = ProvenanceKind.SIMULATED
        telemetry.satellite_name = "SIM-LEO-1"
        telemetry.units = "V"
        telemetry.physical_meaning = "Simulated regulated bus voltage"
        telemetry.metadata["is_simulation"] = True
        telemetry.source_type = SourceType.SIMULATED
        contract = contract_from_telemetry_input(telemetry)
        ch = self.list_channels()[0]
        ch.n_observations = len(telemetry.target_signal)
        return AdapterLoadResult(telemetry, contract, gt, ch, self.describe())


class DatasetRegistry:
    def __init__(self):
        self._adapters: Dict[str, DatasetAdapter] = {}

    def register(self, adapter: DatasetAdapter) -> None:
        self._adapters[adapter.dataset_id] = adapter

    def get(self, dataset_id: str) -> DatasetAdapter:
        if dataset_id not in self._adapters:
            raise KeyError(f"Unknown dataset '{dataset_id}'. Registered: {sorted(self._adapters)}")
        return self._adapters[dataset_id]

    def list_datasets(self) -> List[DatasetDescriptor]:
        return [a.describe() for a in self._adapters.values()]


def default_registry() -> DatasetRegistry:
    registry = DatasetRegistry()
    registry.register(NASATelemanomAdapter())
    registry.register(ESAOpsSatAdapter())
    registry.register(GenericCSVAdapter())
    registry.register(SimulatedDemoAdapter())
    return registry

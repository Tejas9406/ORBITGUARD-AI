"""Strict, Versioned Telemetry Contract System for OrbitGuard AI.

Provides machine-checkable data contracts for every satellite telemetry stream:
- Source and dataset identity (NASA SMAP/MSL, ESA OPS-SAT, SatNOGS, Custom CSV).
- Ordered feature names, units, physical meanings, and data types.
- Timestamp format, sampling frequency, and missing-data policy.
- Train / Validation / Test partition boundary verification.
- Enforces strict contract validation at ingestion and model execution boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class ContractStatus(str, Enum):
    VALID = "VALID"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    INVALID_DIMENSION = "INVALID_DIMENSION"
    INVALID_UNITS = "INVALID_UNITS"
    INVALID_SAMPLING = "INVALID_SAMPLING"
    INVALID_DATA_TYPE = "INVALID_DATA_TYPE"
    MISSING_PARTITIONS = "MISSING_PARTITIONS"


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    unit: str
    data_type: str = "float64"
    physical_meaning: str = "Unspecified measurement"
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    is_target_signal: bool = False


@dataclass
class TelemetryContract:
    contract_version: str  # e.g., "1.0.0"
    source_dataset: str    # "NASA_SMAP_MSL", "ESA_OPS_SAT_AD", "CUSTOM_UPLOAD"
    satellite_name: str    # "SMAP", "MSL", "OPS-SAT-1", "CUSTOM"
    channel_id: str
    features: List[FeatureSpec]
    sampling_rate_hz: Optional[float] = None
    max_allowable_gap_seconds: Optional[float] = None
    requires_normalization: bool = True
    preprocessing_version: str = "standard_causal_v1"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def feature_dim(self) -> int:
        return len(self.features)

    @property
    def feature_names(self) -> List[str]:
        return [f.name for f in self.features]

    @property
    def feature_units(self) -> List[str]:
        return [f.unit for f in self.features]

    @property
    def target_feature_name(self) -> str:
        for f in self.features:
            if f.is_target_signal:
                return f.name
        return self.features[0].name if self.features else ""

    def compute_contract_hash(self) -> str:
        s = json.dumps(
            {
                "version": self.contract_version,
                "source": self.source_dataset,
                "satellite": self.satellite_name,
                "channel": self.channel_id,
                "dim": self.feature_dim,
                "features": [asdict(f) for f in self.features],
            },
            sort_keys=True,
        )
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def validate_data(
        self,
        data: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[ContractStatus, List[str]]:
        """Validate an array or matrix against this contract."""
        issues: List[str] = []

        if data.ndim == 1:
            actual_dim = 1
            n_samples = len(data)
        elif data.ndim == 2:
            n_samples, actual_dim = data.shape
        else:
            return ContractStatus.INVALID_DIMENSION, [f"Data array has unsupported ndim={data.ndim}"]

        if actual_dim != self.feature_dim:
            issues.append(
                f"Feature dimension mismatch: expected {self.feature_dim} features ({self.feature_names}), "
                f"got {actual_dim} columns in data."
            )
            return ContractStatus.INVALID_DIMENSION, issues

        if feature_names is not None:
            if feature_names != self.feature_names:
                issues.append(
                    f"Feature names order mismatch: expected {self.feature_names}, got {feature_names}"
                )
                return ContractStatus.INVALID_SCHEMA, issues

        # Check bounds if specified
        if data.ndim == 1 and self.features:
            spec = self.features[0]
            if spec.expected_min is not None and np.nanmin(data) < spec.expected_min:
                issues.append(f"Feature {spec.name} minimum value {np.nanmin(data)} exceeds bound {spec.expected_min}")
            if spec.expected_max is not None and np.nanmax(data) > spec.expected_max:
                issues.append(f"Feature {spec.name} maximum value {np.nanmax(data)} exceeds bound {spec.expected_max}")

        return ContractStatus.VALID, []


# -------------------------------------------------------------
# Factory Contracts for Known Supported Telemetry Sources
# -------------------------------------------------------------
def get_nasa_contract(channel_id: str, spacecraft: str, feature_dim: int) -> TelemetryContract:
    """Generate contract for NASA SMAP (25-dim) or MSL (55-dim) channels."""
    features = [
        FeatureSpec(
            name=f"{channel_id}_signal",
            unit="normalized_ratio",
            data_type="float64",
            physical_meaning=f"Primary monitored telemetry signal for NASA channel {channel_id}",
            expected_min=-2.0,
            expected_max=2.0,
            is_target_signal=True,
        )
    ]
    for i in range(1, feature_dim):
        features.append(
            FeatureSpec(
                name=f"cmd_aux_{i}",
                unit="binary_flag",
                data_type="float64",
                physical_meaning=f"Command vector / status flag column {i}",
                expected_min=0.0,
                expected_max=1.0,
                is_target_signal=False,
            )
        )

    return TelemetryContract(
        contract_version="1.0.0",
        source_dataset="NASA_SMAP_MSL",
        satellite_name=spacecraft,
        channel_id=channel_id,
        features=features,
        sampling_rate_hz=None,
        max_allowable_gap_seconds=None,
        requires_normalization=False,  # Already normalized to [-1, 1]
        preprocessing_version="telemanom_v2",
        metadata={"l_s": 250, "n_predictions": 10},
    )


def get_esa_opssat_contract(channel_id: str) -> TelemetryContract:
    """Generate contract for ESA OPS-SAT ADCS channels."""
    from .esa_telemetry import ESA_OPSSAT_CHANNEL_METADATA

    meta = ESA_OPSSAT_CHANNEL_METADATA.get(
        channel_id,
        {
            "subsystem": "ADCS",
            "parameter": channel_id,
            "unit": "unspecified",
            "description": f"OPS-SAT CADC mnemonic {channel_id}",
        },
    )

    feature = FeatureSpec(
        name=f"OPS_SAT_{channel_id}",
        unit=meta["unit"],
        data_type="float64",
        physical_meaning=f"{meta['subsystem']}: {meta['parameter']} - {meta['description']}",
        is_target_signal=True,
    )

    return TelemetryContract(
        contract_version="1.0.0",
        source_dataset="ESA_OPS_SAT_AD",
        satellite_name="OPS-SAT-1",
        channel_id=channel_id,
        features=[feature],
        sampling_rate_hz=1.0,
        max_allowable_gap_seconds=10.0,
        requires_normalization=True,
        preprocessing_version="esa_standard_causal_v1",
        metadata={
            "norad_id": 44878,
            "provenance": "Zenodo 15108715",
            "unit": meta["unit"],
            "subsystem": meta["subsystem"],
        },
    )


def get_custom_csv_contract(
    channel_id: str,
    feature_names: List[str],
    units: str = "unspecified",
    satellite_name: str = "user_upload",
    physical_meaning: str = "Unknown / unmapped",
) -> TelemetryContract:
    """Contract for a user-mapped CSV. Semantics stay unknown unless the user supplies them."""
    features = []
    for i, name in enumerate(feature_names or [channel_id]):
        features.append(
            FeatureSpec(
                name=name,
                unit=units,
                physical_meaning=physical_meaning if i == 0 else "Unspecified auxiliary feature",
                is_target_signal=(i == 0),
            )
        )
    return TelemetryContract(
        contract_version="1.0.0",
        source_dataset="CUSTOM_UPLOAD",
        satellite_name=satellite_name,
        channel_id=channel_id,
        features=features,
        requires_normalization=True,
        preprocessing_version="standard_causal_v1",
        metadata={"provenance": "user_upload"},
    )


def contract_from_telemetry_input(telemetry: Any) -> TelemetryContract:
    """Build a contract from a canonical TelemetryInput without inventing semantics."""
    names = getattr(telemetry, "feature_names", None) or [telemetry.channel_id]
    source = getattr(telemetry, "source_dataset", "UNKNOWN")
    if source == "NASA_SMAP_MSL":
        dim = int(telemetry.feature_dim)
        spacecraft = telemetry.satellite_name if telemetry.satellite_name not in ("unknown", "") else "SMAP"
        return get_nasa_contract(telemetry.channel_id, spacecraft, dim)
    if source == "ESA_OPS_SAT_AD":
        cid = str(telemetry.channel_id).replace("ESA_OPSSAT_", "").replace("ESA_", "")
        return get_esa_opssat_contract(cid)
    return get_custom_csv_contract(
        telemetry.channel_id,
        list(names),
        units=getattr(telemetry, "units", "unspecified"),
        satellite_name=getattr(telemetry, "satellite_name", "user_upload"),
        physical_meaning=getattr(telemetry, "physical_meaning", "Unknown / unmapped"),
    )

"""Canonical Telemetry Ingestion and Preprocessing Layer for OrbitGuard AI.

Provides a typed telemetry representation with validation statuses:
- COMPATIBLE: Data fully meets detector requirements.
- COMPATIBLE_WITH_WARNINGS: Data usable after transparent cleaning (NaN fill, outlier cap).
- INCOMPATIBLE: Data cannot be processed (wrong dimensions, too few points).
- INSUFFICIENT_DATA: Not enough valid observations for reliable analysis.

Supports NASA SMAP/MSL .npy arrays, CSV uploads, and raw NumPy arrays.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("orbitguard.ingestion")


class ValidationStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    COMPATIBLE_WITH_WARNINGS = "COMPATIBLE_WITH_WARNINGS"
    INCOMPATIBLE = "INCOMPATIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SourceType(str, Enum):
    NASA_NPY = "NASA_NPY"
    CSV_UPLOAD = "CSV_UPLOAD"
    RAW_ARRAY = "RAW_ARRAY"
    HISTORICAL_DATA = "HISTORICAL_DATA"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    SIMULATED = "SIMULATED"
    LIVE_FEED = "LIVE_FEED"


class ProvenanceKind(str, Enum):
    HISTORICAL_REAL = "historical_real"
    SIMULATED = "simulated"
    USER_UPLOAD = "user_upload"
    LIVE = "live"
    UNKNOWN = "unknown"


@dataclass
class ValidationReport:
    """Transparent record of all preprocessing decisions made on ingested data."""
    status: ValidationStatus
    source_type: SourceType
    original_shape: Tuple[int, ...]
    cleaned_shape: Tuple[int, ...]
    total_observations: int
    valid_observations: int
    nan_count: int
    inf_count: int
    constant_columns: List[int]
    fill_method: str  # "none", "forward_fill", "median_fill"
    warnings: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "source_type": self.source_type.value,
            "original_shape": list(self.original_shape),
            "cleaned_shape": list(self.cleaned_shape),
            "total_observations": self.total_observations,
            "valid_observations": self.valid_observations,
            "nan_count": self.nan_count,
            "inf_count": self.inf_count,
            "constant_columns": self.constant_columns,
            "fill_method": self.fill_method,
            "warnings": self.warnings,
            "blockers": self.blockers,
        }


@dataclass
class TelemetryInput:
    """Canonical typed representation of ingested telemetry data."""
    channel_id: str
    source_type: SourceType
    validation: ValidationReport
    train_data: Optional[np.ndarray]  # (samples, features) — for detectors needing training baseline
    test_data: np.ndarray             # (samples, features) — cleaned evaluation data
    target_signal: np.ndarray         # 1D primary signal (column 0)
    feature_dim: int
    lstm_compatible: bool             # True only for NASA SMAP/MSL arrays with dim 25 or 55
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_dataset: str = "UNKNOWN"
    satellite_name: str = "unknown"
    provenance: ProvenanceKind = ProvenanceKind.UNKNOWN
    timestamps: Optional[List[str]] = None
    timestamp_kind: str = "index"  # "utc" | "index"
    units: str = "unspecified"
    physical_meaning: str = "Unknown / unmapped"
    feature_names: Optional[List[str]] = None
    missing_fraction: float = 0.0
    quality_notes: List[str] = field(default_factory=list)


# ─── Core Preprocessing Functions ────────────────────────────────────────

MIN_OBSERVATIONS = 20
LSTM_SMAP_DIM = 25
LSTM_MSL_DIM = 55


def _detect_issues(data: np.ndarray) -> Tuple[int, int, List[int]]:
    """Count NaNs, Infs, and identify constant-value columns."""
    nan_count = int(np.isnan(data).sum())
    inf_count = int(np.isinf(data).sum())

    if data.ndim == 2:
        constant_cols = [
            int(c) for c in range(data.shape[1])
            if np.nanstd(data[:, c]) < 1e-12
        ]
    else:
        constant_cols = []

    return nan_count, inf_count, constant_cols


def _clean_array(data: np.ndarray) -> Tuple[np.ndarray, str, List[str]]:
    """Clean NaN/Inf values with transparent fill strategy. Returns (cleaned, method, warnings)."""
    warnings = []
    cleaned = data.astype(np.float64).copy()

    # Replace Inf with NaN first
    inf_mask = np.isinf(cleaned)
    if inf_mask.any():
        cleaned[inf_mask] = np.nan
        warnings.append(f"Replaced {int(inf_mask.sum())} Inf values with NaN for safe processing.")

    nan_mask = np.isnan(cleaned)
    if not nan_mask.any():
        return cleaned, "none", warnings

    nan_fraction = nan_mask.sum() / cleaned.size

    if nan_fraction > 0.50:
        warnings.append(f"High missing data fraction ({nan_fraction:.1%}). Results may be unreliable.")

    # Strategy: Forward-fill then backward-fill (causal-safe for streaming data)
    if cleaned.ndim == 1:
        s = pd.Series(cleaned)
        filled = s.ffill().bfill()
        if filled.isna().any():
            filled = filled.fillna(0.0)
        cleaned = filled.to_numpy()
        method = "forward_fill"
    else:
        df = pd.DataFrame(cleaned)
        filled = df.ffill().bfill()
        if filled.isna().any().any():
            filled = filled.fillna(0.0)
        cleaned = filled.to_numpy()
        method = "forward_fill"

    remaining_nan = int(np.isnan(cleaned).sum())
    if remaining_nan > 0:
        cleaned = np.nan_to_num(cleaned, nan=0.0)
        warnings.append(f"Residual {remaining_nan} NaN(s) replaced with 0 after fill.")

    return cleaned, method, warnings


def validate_and_prepare(
    data: np.ndarray,
    source_type: SourceType = SourceType.RAW_ARRAY,
    channel_id: str = "unknown",
    train_data: Optional[np.ndarray] = None,
    min_observations: int = MIN_OBSERVATIONS,
    source_dataset: str = "UNKNOWN",
    satellite_name: str = "unknown",
    provenance: ProvenanceKind = ProvenanceKind.UNKNOWN,
    timestamps: Optional[List[str]] = None,
    timestamp_kind: str = "index",
    units: str = "unspecified",
    physical_meaning: str = "Unknown / unmapped",
    feature_names: Optional[List[str]] = None,
) -> TelemetryInput:
    """Validate and preprocess raw telemetry into canonical TelemetryInput.

    Args:
        data: Raw telemetry array — 1D (univariate) or 2D (multivariate).
        source_type: Origin of the data for tracking.
        channel_id: Identifier for this telemetry stream.
        train_data: Optional training baseline for detectors (Isolation Forest, etc.)
        min_observations: Minimum required valid data points.

    Returns:
        TelemetryInput with validation status and cleaned data.
    """
    original_shape = data.shape
    warnings: List[str] = []
    blockers: List[str] = []

    # Ensure at least 1D
    if data.ndim == 0:
        return _make_incompatible(
            channel_id, source_type, original_shape,
            ["Scalar input is not valid telemetry."]
        )

    # Ensure 2D internally
    if data.ndim == 1:
        work = data.reshape(-1, 1).astype(np.float64)
    elif data.ndim == 2:
        work = data.astype(np.float64)
    else:
        return _make_incompatible(
            channel_id, source_type, original_shape,
            [f"Unsupported array dimensionality: {data.ndim}D (expected 1D or 2D)."]
        )

    total_obs = work.shape[0]

    # Check minimum length
    if total_obs < min_observations:
        return TelemetryInput(
            channel_id=channel_id,
            source_type=source_type,
            validation=ValidationReport(
                status=ValidationStatus.INSUFFICIENT_DATA,
                source_type=source_type,
                original_shape=original_shape,
                cleaned_shape=work.shape,
                total_observations=total_obs,
                valid_observations=total_obs,
                nan_count=0, inf_count=0,
                constant_columns=[],
                fill_method="none",
                warnings=[],
                blockers=[f"Only {total_obs} observations (minimum {min_observations} required)."],
            ),
            train_data=train_data,
            test_data=work,
            target_signal=work[:, 0],
            feature_dim=work.shape[1],
            lstm_compatible=False,
            source_dataset=source_dataset,
            satellite_name=satellite_name,
            provenance=provenance,
        )

    # Detect issues
    nan_count, inf_count, constant_cols = _detect_issues(work)

    if constant_cols:
        warnings.append(f"Columns {constant_cols} have constant values (zero variance).")

    # Clean data
    cleaned, fill_method, clean_warnings = _clean_array(work)
    warnings.extend(clean_warnings)

    # Count valid observations after cleaning
    valid_rows = int((~np.isnan(cleaned).any(axis=1)).sum())
    if valid_rows < min_observations:
        blockers.append(f"Only {valid_rows} valid rows after cleaning (need {min_observations}).")
        status = ValidationStatus.INSUFFICIENT_DATA
    elif warnings:
        status = ValidationStatus.COMPATIBLE_WITH_WARNINGS
    else:
        status = ValidationStatus.COMPATIBLE

    feature_dim = cleaned.shape[1]
    # NASA Telemanom LSTMs are only valid for NASA npy tensors of the documented dims.
    # Matching a column count on an unrelated CSV is not compatibility.
    lstm_ok = source_type == SourceType.NASA_NPY and feature_dim in (LSTM_SMAP_DIM, LSTM_MSL_DIM)
    missing_fraction = float(nan_count / cleaned.size) if cleaned.size else 0.0

    # Clean train data if provided
    cleaned_train = None
    if train_data is not None:
        if train_data.ndim == 1:
            cleaned_train = train_data.reshape(-1, 1).astype(np.float64)
        elif train_data.ndim == 2:
            cleaned_train = train_data.astype(np.float64)
        ct, _, tw = _clean_array(cleaned_train)
        cleaned_train = ct
        if tw:
            warnings.extend([f"[Train] {w}" for w in tw])

    return TelemetryInput(
        channel_id=channel_id,
        source_type=source_type,
        validation=ValidationReport(
            status=status,
            source_type=source_type,
            original_shape=original_shape,
            cleaned_shape=cleaned.shape,
            total_observations=total_obs,
            valid_observations=valid_rows,
            nan_count=nan_count,
            inf_count=inf_count,
            constant_columns=constant_cols,
            fill_method=fill_method,
            warnings=warnings,
            blockers=blockers,
        ),
        train_data=cleaned_train,
        test_data=cleaned,
        target_signal=cleaned[:, 0],
        feature_dim=feature_dim,
        lstm_compatible=lstm_ok,
        source_dataset=source_dataset,
        satellite_name=satellite_name,
        provenance=provenance,
        timestamps=timestamps,
        timestamp_kind=timestamp_kind if timestamps else "index",
        units=units,
        physical_meaning=physical_meaning,
        feature_names=feature_names,
        missing_fraction=missing_fraction,
        quality_notes=list(warnings),
    )


def _make_incompatible(
    channel_id: str,
    source_type: SourceType,
    original_shape: Tuple[int, ...],
    blockers: List[str],
) -> TelemetryInput:
    """Create a TelemetryInput with INCOMPATIBLE status."""
    empty = np.array([], dtype=np.float64).reshape(0, 1)
    return TelemetryInput(
        channel_id=channel_id,
        source_type=source_type,
        validation=ValidationReport(
            status=ValidationStatus.INCOMPATIBLE,
            source_type=source_type,
            original_shape=original_shape,
            cleaned_shape=(0, 0),
            total_observations=0,
            valid_observations=0,
            nan_count=0, inf_count=0,
            constant_columns=[],
            fill_method="none",
            blockers=blockers,
        ),
        train_data=None,
        test_data=empty,
        target_signal=np.array([], dtype=np.float64),
        feature_dim=0,
        lstm_compatible=False,
    )


def ingest_csv(
    file_path: str | Path,
    telemetry_column: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    channel_id: Optional[str] = None,
    feature_columns: Optional[List[str]] = None,
    units: str = "unspecified",
    physical_meaning: str = "Unknown / unmapped",
    satellite_name: str = "user_upload",
) -> TelemetryInput:
    """Ingest a CSV file as telemetry input with explicit column mapping.

    Does not invent timestamps. If timestamp_column is omitted, observations
    remain index-aligned. NASA/ESA LSTM models are never implied by column count.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)
    cid = channel_id or path.stem
    available = list(df.columns)

    if feature_columns:
        missing = [c for c in feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Feature columns not found: {missing}. Available: {available}")
        matrix = df[feature_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
        names = list(feature_columns)
        telemetry_column = feature_columns[0]
        values = matrix
    elif telemetry_column:
        if telemetry_column not in df.columns:
            raise ValueError(f"Column '{telemetry_column}' not found in CSV. Available: {available}")
        values = pd.to_numeric(df[telemetry_column], errors="coerce").to_numpy()
        names = [telemetry_column]
    else:
        names = []
        values = None
        for col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.notna().sum() >= MIN_OBSERVATIONS:
                values = numeric.to_numpy()
                telemetry_column = col
                names = [col]
                break
        if values is None:
            return _make_incompatible(
                cid, SourceType.CSV_UPLOAD, (len(df), len(df.columns)),
                ["No column with >= 20 valid numeric observations found."]
            )

    parsed_ts: Optional[List[str]] = None
    ts_kind = "index"
    if timestamp_column:
        if timestamp_column not in df.columns:
            raise ValueError(f"Timestamp column '{timestamp_column}' not found. Available: {available}")
        parsed = pd.to_datetime(df[timestamp_column], errors="coerce", utc=True)
        if parsed.notna().sum() < MIN_OBSERVATIONS:
            raise ValueError(
                f"Timestamp column '{timestamp_column}' could not be parsed into enough valid datetimes."
            )
        parsed_ts = [None if pd.isna(v) else v.isoformat() for v in parsed]
        ts_kind = "utc"

    # Automatically carve out 30% for training so Isolation Forest has a baseline
    split_idx = max(int(len(values) * 0.3), MIN_OBSERVATIONS)
    if split_idx >= len(values):
        split_idx = len(values) // 2
    
    train_data = values[:split_idx]
    test_data = values
    
    # keep parsed_ts full length aligned with values

    inp = validate_and_prepare(
        test_data,
        source_type=SourceType.CSV_UPLOAD,
        channel_id=cid,
        train_data=train_data,
        source_dataset="CUSTOM_UPLOAD",
        satellite_name=satellite_name,
        provenance=ProvenanceKind.USER_UPLOAD,
        timestamps=parsed_ts,
        timestamp_kind=ts_kind,
        units=units,
        physical_meaning=physical_meaning,
        feature_names=names,
    )

    inp.metadata["source_file"] = path.name
    if telemetry_column:
        inp.metadata["telemetry_column"] = telemetry_column
    if timestamp_column:
        inp.metadata["timestamp_column"] = timestamp_column
    if parsed_ts:
        inp.metadata["timestamps"] = parsed_ts
    return inp


def ingest_nasa_channel(
    root: str | Path,
    channel_id: str,
) -> TelemetryInput:
    """Ingest a NASA SMAP/MSL channel from the standard Telemanom directory layout."""
    root = Path(root)
    train_path = root / "data" / "train" / f"{channel_id}.npy"
    test_path = root / "data" / "test" / f"{channel_id}.npy"

    if not test_path.is_file():
        raise FileNotFoundError(f"Test data not found: {test_path}")
    if not train_path.is_file():
        raise FileNotFoundError(f"Train data not found: {train_path}")

    train = np.load(train_path).astype(np.float64)
    test = np.load(test_path).astype(np.float64)

    inp = validate_and_prepare(
        test,
        source_type=SourceType.NASA_NPY,
        channel_id=channel_id,
        train_data=train,
        source_dataset="NASA_SMAP_MSL",
        satellite_name="unknown",
        provenance=ProvenanceKind.HISTORICAL_REAL,
        timestamp_kind="index",
        units="normalized_ratio",
        physical_meaning="Unknown / unmapped (anonymized NASA Telemanom channel)",
        feature_names=[f"{channel_id}_signal"] + [f"cmd_aux_{i}" for i in range(1, test.shape[1] if test.ndim == 2 else 1)],
    )
    inp.metadata["train_file"] = train_path.name
    inp.metadata["test_file"] = test_path.name
    return inp

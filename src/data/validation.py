"""Telemetry data validation module for OrbitGuard AI.

Provides rigorous schema and data integrity verification for incoming satellite
telemetry streams, protecting downstream preprocessing, statistical baselines,
and ML detectors from corrupted or incomplete inputs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class TelemetryValidationError(ValueError):
    """Base exception for all telemetry data validation errors."""
    pass


class EmptyDataError(TelemetryValidationError):
    """Raised when the telemetry dataset is empty (0 rows or 0 columns)."""
    pass


class MissingColumnError(TelemetryValidationError, KeyError):
    """Raised when required timestamp or telemetry channels are missing."""
    pass


class InvalidTimestampError(TelemetryValidationError):
    """Raised when timestamp strings cannot be parsed or contain invalid dates."""
    pass


class NonNumericTelemetryError(TelemetryValidationError, TypeError):
    """Raised when telemetry channels contain non-numeric entries."""
    pass


class MissingValueError(TelemetryValidationError):
    """Raised when missing or null values (NaN, None, NaT) are detected."""
    pass


class DuplicateRecordError(TelemetryValidationError):
    """Raised when duplicate timestamps or duplicate observation rows are detected."""
    pass


@dataclass(frozen=True)
class ValidationReport:
    """Summary report detailing telemetry validation outcomes.

    Attributes:
        is_valid: True if telemetry satisfies all required checks, False otherwise.
        errors: List of descriptive error messages explaining failed checks.
        warnings: List of non-fatal warning messages for downstream telemetry consumers.
        timestamp_col: Name of the verified timestamp column.
        telemetry_cols: List of validated telemetry channel column names.
        total_rows: Total number of observations in the dataset.
        duplicate_timestamp_count: Count of non-unique timestamps found.
        duplicate_row_count: Count of non-unique complete rows found.
        missing_values_by_column: Dictionary mapping column names to missing value counts.
        invalid_timestamp_count: Count of malformed/unparseable timestamps found.
        non_numeric_columns: Dictionary mapping column names to row indices with non-numeric values.
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp_col: str = "timestamp"
    telemetry_cols: List[str] = field(default_factory=list)
    total_rows: int = 0
    duplicate_timestamp_count: int = 0
    duplicate_row_count: int = 0
    missing_values_by_column: Dict[str, int] = field(default_factory=dict)
    invalid_timestamp_count: int = 0
    non_numeric_columns: Dict[str, List[int]] = field(default_factory=dict)


def validate_telemetry(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    telemetry_cols: Optional[List[str]] = None,
    allow_duplicates: bool = False,
    allow_missing: bool = False,
    raise_on_error: bool = True,
) -> ValidationReport:
    """Validates that a DataFrame conforms to the satellite telemetry contract.

    This function performs non-destructive validation:
    - Never mutates the input DataFrame.
    - Never silently drops rows with errors.
    - Never replaces missing values with default zeros.
    - Preserves all channel identifiers and row indexing.

    Args:
        df: Input pandas DataFrame containing telemetry observations.
        timestamp_col: Name of the column representing temporal stamps. Defaults to "timestamp".
        telemetry_cols: Optional list of column names for telemetry channels to validate.
            If None, all columns other than `timestamp_col` (and any 'is_anomaly' / 'label' column)
            are treated as telemetry channels.
        allow_duplicates: If True, duplicate timestamps and rows will not trigger errors. Defaults to False.
        allow_missing: If True, null/NaN values will not trigger errors. Defaults to False.
        raise_on_error: If True, raises the first matching TelemetryValidationError upon detection.
            If False, aggregates all detected issues into the returned ValidationReport.

    Returns:
        ValidationReport: A detailed structured report of data validation results.

    Raises:
        TypeError: If `df` is not a pandas DataFrame.
        EmptyDataError: If `df` contains 0 rows or 0 columns.
        MissingColumnError: If `timestamp_col` or specified `telemetry_cols` are missing.
        InvalidTimestampError: If timestamp values cannot be converted to valid datetimes.
        NonNumericTelemetryError: If telemetry channels contain non-numeric entries.
        MissingValueError: If null/NaN values are detected and `allow_missing` is False.
        DuplicateRecordError: If duplicate timestamps or rows are detected and `allow_duplicates` is False.
    """
    if not isinstance(df, pd.DataFrame):
        msg = f"Input telemetry must be a pandas DataFrame, got {type(df).__name__}."
        if raise_on_error:
            raise TypeError(msg)
        return ValidationReport(is_valid=False, errors=[msg])

    errors: List[str] = []
    warnings: List[str] = []
    missing_values_by_column: Dict[str, int] = {}
    non_numeric_columns: Dict[str, List[int]] = {}

    # Check for empty dataframe
    if df.empty or len(df) == 0 or df.shape[1] == 0:
        msg = "Telemetry DataFrame is empty (0 rows or 0 columns)."
        if raise_on_error:
            raise EmptyDataError(msg)
        return ValidationReport(
            is_valid=False,
            errors=[msg],
            timestamp_col=timestamp_col,
            telemetry_cols=[],
            total_rows=0,
        )

    # Validate timestamp column presence
    if timestamp_col not in df.columns:
        msg = f"Required timestamp column '{timestamp_col}' not found in telemetry DataFrame."
        if raise_on_error:
            raise MissingColumnError(msg)
        errors.append(msg)

    # Resolve and validate telemetry channels
    resolved_telemetry_cols: List[str] = []
    if telemetry_cols is not None:
        if len(telemetry_cols) == 0:
            msg = "telemetry_cols parameter was provided but is empty; at least one telemetry channel is required."
            if raise_on_error:
                raise MissingColumnError(msg)
            errors.append(msg)
        else:
            missing_channels = [col for col in telemetry_cols if col not in df.columns]
            if missing_channels:
                msg = f"Missing required telemetry channel(s): {missing_channels}."
                if raise_on_error:
                    raise MissingColumnError(msg)
                errors.append(msg)
            resolved_telemetry_cols = [col for col in telemetry_cols if col in df.columns]
    else:
        # Automatically infer non-timestamp and non-ground-truth channels
        excluded = {timestamp_col, "is_anomaly", "anomaly_type", "label", "ground_truth"}
        resolved_telemetry_cols = [col for col in df.columns if col not in excluded]
        if not resolved_telemetry_cols:
            msg = "No telemetry channels found in DataFrame after excluding timestamp and label columns."
            if raise_on_error:
                raise MissingColumnError(msg)
            errors.append(msg)

    # Timestamp validity and missingness
    invalid_timestamp_count = 0
    if timestamp_col in df.columns:
        ts_series = df[timestamp_col]
        # Missing timestamps
        ts_null_count = int(ts_series.isna().sum())
        if ts_null_count > 0:
            missing_values_by_column[timestamp_col] = ts_null_count
            if not allow_missing:
                msg = f"Timestamp column '{timestamp_col}' contains {ts_null_count} null/missing values."
                if raise_on_error:
                    raise MissingValueError(msg)
                errors.append(msg)

        # Parseable timestamps check
        # Convert non-null values to datetime to identify unparseable entries
        parsed_ts = pd.to_datetime(ts_series, errors="coerce")
        # Identify rows where original value was non-null but parsed result is NaT
        unparseable_mask = ts_series.notna() & parsed_ts.isna()
        invalid_timestamp_count = int(unparseable_mask.sum())
        if invalid_timestamp_count > 0:
            msg = f"Timestamp column '{timestamp_col}' contains {invalid_timestamp_count} unparseable/invalid timestamps."
            if raise_on_error:
                raise InvalidTimestampError(msg)
            errors.append(msg)

    # Duplicates check
    dup_timestamp_count = 0
    dup_row_count = int(df.duplicated().sum())
    if timestamp_col in df.columns:
        dup_timestamp_count = int(df[timestamp_col].duplicated().sum())

    if not allow_duplicates:
        if dup_timestamp_count > 0:
            msg = f"Telemetry contains {dup_timestamp_count} duplicate timestamp entries in column '{timestamp_col}'."
            if raise_on_error:
                raise DuplicateRecordError(msg)
            errors.append(msg)
        elif dup_row_count > 0:
            msg = f"Telemetry contains {dup_row_count} duplicate complete observation rows."
            if raise_on_error:
                raise DuplicateRecordError(msg)
            errors.append(msg)

    # Telemetry channels numeric and missing value checks
    for col in resolved_telemetry_cols:
        col_series = df[col]

        # Missing values
        null_count = int(col_series.isna().sum())
        if null_count > 0:
            missing_values_by_column[col] = null_count
            if not allow_missing:
                msg = f"Telemetry channel '{col}' contains {null_count} missing values."
                if raise_on_error:
                    raise MissingValueError(msg)
                errors.append(msg)

        # Numeric validity
        if not pd.api.types.is_numeric_dtype(col_series):
            # Attempt coercion to locate offending row indices
            coerced = pd.to_numeric(col_series, errors="coerce")
            bad_indices = col_series[col_series.notna() & coerced.isna()].index.tolist()
            if bad_indices or not pd.api.types.is_numeric_dtype(coerced):
                non_numeric_columns[col] = bad_indices
                msg = f"Telemetry channel '{col}' contains non-numeric values at indices: {bad_indices[:5]}{'...' if len(bad_indices) > 5 else ''}."
                if raise_on_error:
                    raise NonNumericTelemetryError(msg)
                errors.append(msg)

    is_valid = len(errors) == 0

    return ValidationReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        timestamp_col=timestamp_col,
        telemetry_cols=resolved_telemetry_cols,
        total_rows=len(df),
        duplicate_timestamp_count=dup_timestamp_count,
        duplicate_row_count=dup_row_count,
        missing_values_by_column=missing_values_by_column,
        invalid_timestamp_count=invalid_timestamp_count,
        non_numeric_columns=non_numeric_columns,
    )

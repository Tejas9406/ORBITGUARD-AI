"""Unit tests for telemetry data validation module."""

import numpy as np
import pandas as pd
import pytest

from src.data.validation import (
    DuplicateRecordError,
    EmptyDataError,
    InvalidTimestampError,
    MissingColumnError,
    MissingValueError,
    NonNumericTelemetryError,
    TelemetryValidationError,
    ValidationReport,
    validate_telemetry,
)
import src.data_validation as dv_alias


@pytest.fixture
def valid_telemetry_df() -> pd.DataFrame:
    """Fixture providing a small, valid in-memory telemetry dataset."""
    return pd.DataFrame({
        "timestamp": [
            "2026-10-09T00:00:00Z",
            "2026-10-09T00:01:00Z",
            "2026-10-09T00:02:00Z",
            "2026-10-09T00:03:00Z",
        ],
        "solar_voltage": [28.2, 28.1, 28.3, 28.0],
        "battery_temp": [22.4, 22.5, 22.6, 22.7],
        "gyro_x": [0.01, -0.02, 0.00, 0.03],
    })


def test_valid_telemetry_default_args(valid_telemetry_df):
    """Test that well-formed telemetry passes validation and returns valid report."""
    report = validate_telemetry(valid_telemetry_df)
    assert isinstance(report, ValidationReport)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.total_rows == 4
    assert set(report.telemetry_cols) == {"solar_voltage", "battery_temp", "gyro_x"}
    assert report.duplicate_timestamp_count == 0
    assert report.duplicate_row_count == 0


def test_valid_telemetry_custom_columns():
    """Test validation with customized timestamp and telemetry column names."""
    df = pd.DataFrame({
        "time_utc": ["2026-10-09 10:00:00", "2026-10-09 10:01:00"],
        "temp_channel_1": [15.5, 16.0],
        "aux_voltage": [3.3, 3.29],
        "ignored_col": ["meta1", "meta2"],
    })
    report = validate_telemetry(
        df,
        timestamp_col="time_utc",
        telemetry_cols=["temp_channel_1", "aux_voltage"],
    )
    assert report.is_valid is True
    assert report.timestamp_col == "time_utc"
    assert report.telemetry_cols == ["temp_channel_1", "aux_voltage"]


def test_non_dataframe_input():
    """Test that passing non-DataFrame raises TypeError in strict mode and invalid report in non-strict."""
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_telemetry({"timestamp": ["2026-01-01"], "val": [1.0]})

    report = validate_telemetry([1, 2, 3], raise_on_error=False)
    assert report.is_valid is False
    assert any("must be a pandas DataFrame" in err for err in report.errors)


def test_empty_dataframe():
    """Test that empty DataFrames raise EmptyDataError."""
    empty_df = pd.DataFrame()
    with pytest.raises(EmptyDataError, match="empty"):
        validate_telemetry(empty_df)

    # Empty with columns but 0 rows
    empty_with_cols = pd.DataFrame(columns=["timestamp", "solar_voltage"])
    with pytest.raises(EmptyDataError):
        validate_telemetry(empty_with_cols)

    report = validate_telemetry(empty_df, raise_on_error=False)
    assert report.is_valid is False
    assert any("empty" in err for err in report.errors)


def test_missing_timestamp_column(valid_telemetry_df):
    """Test that missing required timestamp column raises MissingColumnError."""
    df_no_ts = valid_telemetry_df.drop(columns=["timestamp"])
    with pytest.raises(MissingColumnError, match="Required timestamp column 'timestamp' not found"):
        validate_telemetry(df_no_ts)

    report = validate_telemetry(df_no_ts, raise_on_error=False)
    assert report.is_valid is False
    assert any("Required timestamp column 'timestamp' not found" in err for err in report.errors)


def test_missing_specified_telemetry_column(valid_telemetry_df):
    """Test that missing explicitly requested telemetry channel raises MissingColumnError."""
    with pytest.raises(MissingColumnError, match="Missing required telemetry channel"):
        validate_telemetry(valid_telemetry_df, telemetry_cols=["solar_voltage", "non_existent_channel"])

    # Empty list of telemetry channels requested
    with pytest.raises(MissingColumnError, match="telemetry_cols parameter was provided but is empty"):
        validate_telemetry(valid_telemetry_df, telemetry_cols=[])


def test_missing_telemetry_channels_when_inferred():
    """Test DataFrame containing only a timestamp column raises MissingColumnError."""
    df_only_ts = pd.DataFrame({"timestamp": ["2026-10-09T00:00:00Z", "2026-10-09T00:01:00Z"]})
    with pytest.raises(MissingColumnError, match="No telemetry channels found"):
        validate_telemetry(df_only_ts)


def test_malformed_unparseable_timestamps():
    """Test that malformed timestamp strings trigger InvalidTimestampError."""
    df = pd.DataFrame({
        "timestamp": ["2026-10-09T00:00:00Z", "INVALID_DATE_STRING", "2026-10-09T00:02:00Z"],
        "voltage": [28.0, 28.1, 28.2],
    })
    with pytest.raises(InvalidTimestampError, match="unparseable/invalid timestamps"):
        validate_telemetry(df)

    report = validate_telemetry(df, raise_on_error=False)
    assert report.is_valid is False
    assert report.invalid_timestamp_count == 1
    assert any("unparseable/invalid timestamps" in err for err in report.errors)


def test_missing_values_in_telemetry_channels(valid_telemetry_df):
    """Test that NaN values in telemetry channels trigger MissingValueError."""
    df_with_nan = valid_telemetry_df.copy()
    df_with_nan.loc[2, "solar_voltage"] = np.nan

    with pytest.raises(MissingValueError, match="contains 1 missing values"):
        validate_telemetry(df_with_nan)

    report = validate_telemetry(df_with_nan, raise_on_error=False)
    assert report.is_valid is False
    assert report.missing_values_by_column.get("solar_voltage") == 1


def test_missing_values_in_timestamp_column(valid_telemetry_df):
    """Test that missing values in timestamp column trigger MissingValueError."""
    df_with_null_ts = valid_telemetry_df.copy()
    df_with_null_ts.loc[1, "timestamp"] = None

    with pytest.raises(MissingValueError, match="contains 1 null/missing values"):
        validate_telemetry(df_with_null_ts)


def test_duplicate_timestamps(valid_telemetry_df):
    """Test that duplicate timestamps trigger DuplicateRecordError."""
    df_dup = valid_telemetry_df.copy()
    # Create duplicate timestamp
    df_dup.loc[2, "timestamp"] = df_dup.loc[1, "timestamp"]

    with pytest.raises(DuplicateRecordError, match="duplicate timestamp entries"):
        validate_telemetry(df_dup)

    report = validate_telemetry(df_dup, raise_on_error=False)
    assert report.is_valid is False
    assert report.duplicate_timestamp_count > 0


def test_duplicate_entire_rows(valid_telemetry_df):
    """Test that duplicate complete rows trigger DuplicateRecordError."""
    df_dup_rows = pd.concat([valid_telemetry_df, valid_telemetry_df.iloc[[0]]], ignore_index=True)

    with pytest.raises(DuplicateRecordError):
        validate_telemetry(df_dup_rows)


def test_non_numeric_telemetry_channels(valid_telemetry_df):
    """Test that string or non-numeric entries in telemetry channels trigger NonNumericTelemetryError."""
    df_bad_type = valid_telemetry_df.copy()
    df_bad_type["solar_voltage"] = ["28.0", "glitch_string", "28.2", "28.3"]

    with pytest.raises(NonNumericTelemetryError, match="contains non-numeric values"):
        validate_telemetry(df_bad_type)

    report = validate_telemetry(df_bad_type, raise_on_error=False)
    assert report.is_valid is False
    assert "solar_voltage" in report.non_numeric_columns
    assert 1 in report.non_numeric_columns["solar_voltage"]


def test_input_immutability(valid_telemetry_df):
    """Test that validation never mutates input DataFrame or silently drops rows/fills nulls."""
    df_copy = valid_telemetry_df.copy(deep=True)
    report = validate_telemetry(valid_telemetry_df)

    assert report.is_valid is True
    # Ensure exact identity and values remain untouched
    pd.testing.assert_frame_equal(valid_telemetry_df, df_copy)


def test_allow_flags_behavior(valid_telemetry_df):
    """Test that allow_duplicates and allow_missing relax strict checks when requested."""
    df_imperfect = valid_telemetry_df.copy()
    df_imperfect.loc[2, "solar_voltage"] = np.nan
    df_imperfect.loc[3, "timestamp"] = df_imperfect.loc[0, "timestamp"]

    # When flags are True, validation passes with non-fatal recording
    report = validate_telemetry(
        df_imperfect,
        allow_duplicates=True,
        allow_missing=True,
        raise_on_error=False,
    )
    assert report.is_valid is True
    assert report.duplicate_timestamp_count == 1
    assert report.missing_values_by_column["solar_voltage"] == 1


def test_alias_module_reexport():
    """Verify that src.data_validation provides identical interface without duplication."""
    assert dv_alias.validate_telemetry is validate_telemetry
    assert dv_alias.ValidationReport is ValidationReport
    assert dv_alias.TelemetryValidationError is TelemetryValidationError
    assert dv_alias.EmptyDataError is EmptyDataError
    assert dv_alias.MissingColumnError is MissingColumnError
    assert dv_alias.InvalidTimestampError is InvalidTimestampError
    assert dv_alias.NonNumericTelemetryError is NonNumericTelemetryError
    assert dv_alias.MissingValueError is MissingValueError
    assert dv_alias.DuplicateRecordError is DuplicateRecordError

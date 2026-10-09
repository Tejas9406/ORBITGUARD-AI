"""Unit tests for synthetic sample telemetry dataset and provenance consistency."""

from pathlib import Path
import pandas as pd
import pytest

from src.data.synthetic import generate_synthetic_telemetry
from src.data.validation import validate_telemetry


DATA_FILE_PATH = Path("data") / "sample_telemetry.csv"


def test_dataset_file_exists():
    """Verify sample telemetry CSV file exists on disk."""
    assert DATA_FILE_PATH.exists(), f"Sample dataset not found at {DATA_FILE_PATH}"


@pytest.fixture
def sample_telemetry_df() -> pd.DataFrame:
    """Fixture providing loaded sample telemetry DataFrame."""
    return pd.read_csv(DATA_FILE_PATH)


def test_dataset_shape_and_columns(sample_telemetry_df):
    """Test expected row count and required schema columns."""
    assert len(sample_telemetry_df) == 1440
    expected_columns = [
        "timestamp",
        "solar_panel_voltage",
        "battery_temp",
        "battery_current",
        "gyro_x",
        "gyro_y",
        "gyro_z",
        "is_anomaly",
        "anomaly_type",
    ]
    assert list(sample_telemetry_df.columns) == expected_columns


def test_dataset_timestamps_integrity(sample_telemetry_df):
    """Verify timestamps are strictly monotonic, 1-minute steps, and non-null."""
    ts_series = pd.to_datetime(sample_telemetry_df["timestamp"], utc=True)
    assert ts_series.is_monotonic_increasing
    time_diffs = ts_series.diff()[1:]
    assert (time_diffs == pd.Timedelta(minutes=1)).all()


def test_dataset_anomaly_labels_distribution(sample_telemetry_df):
    """Verify ground truth anomaly labels match documented counts and types."""
    # Binary is_anomaly checks
    assert set(sample_telemetry_df["is_anomaly"].unique()) == {0, 1}
    assert sample_telemetry_df["is_anomaly"].sum() == 53

    # Anomaly type breakdown
    type_counts = sample_telemetry_df["anomaly_type"].value_counts().to_dict()
    assert type_counts == {
        "nominal": 1387,
        "gyro_glitch": 21,
        "temperature_spike": 16,
        "voltage_drop": 16,
    }

    # Cross-consistency: is_anomaly == 1 iff anomaly_type != 'nominal'
    assert ((sample_telemetry_df["is_anomaly"] == 1) == (sample_telemetry_df["anomaly_type"] != "nominal")).all()


def test_dataset_validation_passes(sample_telemetry_df):
    """Verify validate_telemetry confirms dataset validity with zero errors."""
    report = validate_telemetry(sample_telemetry_df, raise_on_error=True)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.total_rows == 1440
    assert report.duplicate_timestamp_count == 0
    assert report.duplicate_row_count == 0
    assert report.invalid_timestamp_count == 0
    assert report.missing_values_by_column == {}
    assert set(report.telemetry_cols) == {
        "solar_panel_voltage",
        "battery_temp",
        "battery_current",
        "gyro_x",
        "gyro_y",
        "gyro_z",
    }


def test_generator_determinism_and_reproducibility(sample_telemetry_df):
    """Verify that generating with fixed seed reproduces the exact dataset."""
    fresh_df = generate_synthetic_telemetry(n_minutes=1440, seed=42)
    pd.testing.assert_frame_equal(sample_telemetry_df, fresh_df)

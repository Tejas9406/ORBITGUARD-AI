"""Unit tests for telemetry loading, feature/label separation, and chronological splitting."""

from pathlib import Path
import pandas as pd
import pytest

from src.data.loader import (
    chronological_train_test_split,
    load_telemetry,
    split_features_and_labels,
)
from src.data.validation import EmptyDataError


@pytest.fixture
def sample_csv_path() -> Path:
    return Path("data") / "sample_telemetry.csv"


def test_load_telemetry_valid(sample_csv_path):
    """Test loading valid sample dataset with validation enabled."""
    df = load_telemetry(sample_csv_path, validate=True)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1440
    assert "timestamp" in df.columns
    assert "is_anomaly" in df.columns


def test_load_telemetry_missing_file():
    """Test loading nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        load_telemetry("data/nonexistent_file_12345.csv")


def test_load_telemetry_empty_file(tmp_path):
    """Test loading an empty file raises EmptyDataError."""
    empty_file = tmp_path / "empty_telemetry.csv"
    empty_file.write_text("")
    with pytest.raises(EmptyDataError):
        load_telemetry(empty_file)


def test_split_features_and_labels_default(sample_csv_path):
    """Test standard feature and label separation preserves rows and prevents leakage."""
    df = load_telemetry(sample_csv_path)
    X, y = split_features_and_labels(df)

    # Features check
    assert len(X) == len(df)
    assert "is_anomaly" not in X.columns
    assert "anomaly_type" not in X.columns
    assert "timestamp" in X.columns
    assert "solar_panel_voltage" in X.columns
    assert "battery_temp" in X.columns

    # Labels check
    assert len(y) == len(df)
    assert list(y.columns) == ["is_anomaly", "anomaly_type"]
    assert y["is_anomaly"].sum() == 53

    # Index alignment check
    pd.testing.assert_index_equal(X.index, y.index)


def test_split_features_and_labels_custom():
    """Test feature/label split with custom specified label columns."""
    df = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
        "voltage": [28.0, 28.1],
        "custom_label": [0, 1],
    })
    X, y = split_features_and_labels(df, label_cols=["custom_label"])
    assert list(X.columns) == ["timestamp", "voltage"]
    assert list(y.columns) == ["custom_label"]


def test_split_features_and_labels_empty_df():
    """Test that splitting an empty DataFrame raises ValueError."""
    with pytest.raises(ValueError, match="Cannot split"):
        split_features_and_labels(pd.DataFrame())


def test_chronological_train_test_split(sample_csv_path):
    """Test that train/test split is strictly chronological with zero row loss."""
    df = load_telemetry(sample_csv_path)
    train_df, test_df = chronological_train_test_split(df, train_fraction=0.7)

    # Total conservation
    assert len(train_df) + len(test_df) == len(df)
    assert len(train_df) == int(1440 * 0.7)
    assert len(test_df) == 1440 - int(1440 * 0.7)

    # Chronological ordering check
    max_train_ts = train_df["timestamp"].max()
    min_test_ts = test_df["timestamp"].min()
    assert max_train_ts < min_test_ts, "Train timestamp overlaps with or occurs after test timestamp!"


def test_chronological_split_invalid_fraction(sample_csv_path):
    """Test that invalid split fractions raise ValueError."""
    df = load_telemetry(sample_csv_path)
    for bad_fraction in [-0.2, 0.0, 1.0, 1.5]:
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            chronological_train_test_split(df, train_fraction=bad_fraction)


def test_chronological_split_small_dataset():
    """Test boundary behavior on very small datasets."""
    # 2 rows
    small_df = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
        "voltage": [28.0, 28.1],
    })
    train, test = chronological_train_test_split(small_df, train_fraction=0.5)
    assert len(train) == 1
    assert len(test) == 1

    # 1 row
    single_row_df = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z"],
        "voltage": [28.0],
    })
    with pytest.raises(ValueError, match="at least 2 rows"):
        chronological_train_test_split(single_row_df)


def test_chronological_split_sorts_unsorted_data():
    """Test that input data with scrambled timestamps is chronologically ordered."""
    scrambled_df = pd.DataFrame({
        "timestamp": ["2026-10-01T00:05:00Z", "2026-10-01T00:01:00Z", "2026-10-01T00:03:00Z", "2026-10-01T00:02:00Z"],
        "voltage": [28.5, 28.1, 28.3, 28.2],
    })
    train, test = chronological_train_test_split(scrambled_df, train_fraction=0.5)
    assert list(train["timestamp"]) == ["2026-10-01T00:01:00Z", "2026-10-01T00:02:00Z"]
    assert list(test["timestamp"]) == ["2026-10-01T00:03:00Z", "2026-10-01T00:05:00Z"]

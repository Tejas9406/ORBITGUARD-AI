"""Telemetry loading, dataset splitting, and feature/label separation module.

Provides safe I/O and strict chronological partitioning for satellite telemetry
data, ensuring zero future-to-past data leakage and preserving alignment across
observations, channels, and evaluation ground truth.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
import pandas as pd

from src.data.validation import (
    EmptyDataError,
    validate_telemetry,
)


DEFAULT_LABEL_COLS = ["is_anomaly", "anomaly_type"]


def load_telemetry(
    file_path: Union[str, Path] = "data/sample_telemetry.csv",
    validate: bool = True,
    timestamp_col: str = "timestamp",
    telemetry_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Loads a telemetry CSV dataset and validates its schema and integrity.

    Args:
        file_path: Path to the telemetry CSV file. Defaults to "data/sample_telemetry.csv".
        validate: If True, executes `validate_telemetry` in strict raising mode. Defaults to True.
        timestamp_col: Name of the timestamp column. Defaults to "timestamp".
        telemetry_cols: Optional explicit list of telemetry channel column names.

    Returns:
        pd.DataFrame containing loaded and verified telemetry observations.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        EmptyDataError: If the file is empty or contains no records.
        TelemetryValidationError: If validation fails under strict mode.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Telemetry file not found at: {path.resolve()}")

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise EmptyDataError(f"Telemetry file '{path}' is empty.")

    if df.empty or len(df) == 0:
        raise EmptyDataError(f"Telemetry file '{path}' contains 0 records.")

    if validate:
        # Validate schema, numeric channels, timestamps, and duplicates
        validate_telemetry(
            df=df,
            timestamp_col=timestamp_col,
            telemetry_cols=telemetry_cols,
            raise_on_error=True,
        )

    return df


def split_features_and_labels(
    df: pd.DataFrame,
    label_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Separates telemetry feature columns from evaluation ground truth labels.

    Guarantees that evaluation labels (`is_anomaly`, `anomaly_type`) never
    enter the model feature matrix, while preserving identical index alignment.

    Args:
        df: Input telemetry DataFrame.
        label_cols: Optional list of column names to isolate as ground truth labels.
            Defaults to ["is_anomaly", "anomaly_type"] (filtering for columns present).

    Returns:
        Tuple of (X, y):
            - X: DataFrame containing timestamps and engineering telemetry channels only.
            - y: DataFrame containing evaluation ground-truth label columns only.

    Raises:
        ValueError: If input DataFrame is empty or contains no feature columns.
    """
    if df.empty:
        raise ValueError("Cannot split features and labels on an empty DataFrame.")

    target_label_cols = (
        label_cols
        if label_cols is not None
        else [c for c in DEFAULT_LABEL_COLS if c in df.columns]
    )

    feature_cols = [c for c in df.columns if c not in target_label_cols]
    if not feature_cols:
        raise ValueError("DataFrame contains no feature columns after removing label columns.")

    X = df[feature_cols].copy()
    y = df[target_label_cols].copy() if target_label_cols else pd.DataFrame(index=df.index)

    return X, y


def chronological_train_test_split(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
    timestamp_col: str = "timestamp",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Performs a strict chronological train/test split on time-series telemetry.

    Unlike random K-Fold or shuffled splits, this function strictly assigns the
    earlier time window to the training set and the subsequent time window to the
    testing set. This prevents temporal data leakage and simulates operational deployment.

    Boundary Behavior:
    - Observations with index < split_idx are assigned to training.
    - Observations with index >= split_idx are assigned to testing.
    - Zero observations are dropped: len(train) + len(test) == len(df).
    - Preserves all original column names and values without modification.

    Args:
        df: Input telemetry DataFrame.
        train_fraction: Proportion of earliest records allocated to training (0.0 < train_fraction < 1.0).
            Defaults to 0.7 (70% train, 30% test).
        timestamp_col: Column name used to verify temporal ordering. Defaults to "timestamp".

    Returns:
        Tuple of (train_df, test_df).

    Raises:
        ValueError: If `train_fraction` is not between 0.0 and 1.0, or if `df` contains fewer than 2 rows.
    """
    if not (0.0 < train_fraction < 1.0):
        raise ValueError(
            f"train_fraction must be strictly between 0.0 and 1.0, got {train_fraction}."
        )

    n_rows = len(df)
    if n_rows < 2:
        raise ValueError(
            f"Telemetry DataFrame must have at least 2 rows to split, got {n_rows}."
        )

    # Ensure chronological order
    if timestamp_col in df.columns:
        parsed_ts = pd.to_datetime(df[timestamp_col], errors="coerce")
        if not parsed_ts.is_monotonic_increasing:
            df_sorted = df.sort_values(by=timestamp_col).copy()
        else:
            df_sorted = df.copy()
    else:
        df_sorted = df.copy()

    split_idx = int(n_rows * train_fraction)
    # Ensure both splits receive at least 1 observation
    split_idx = max(1, min(split_idx, n_rows - 1))

    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()

    return train_df, test_df

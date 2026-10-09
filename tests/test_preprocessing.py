"""Unit tests for leakage-safe telemetry preprocessing and temporal feature engineering."""

import numpy as np
import pandas as pd
import pytest

from src.data.loader import (
    chronological_train_test_split,
    load_telemetry,
    split_features_and_labels,
)
from src.data.preprocessing import (
    NotFittedError,
    TelemetryPreprocessor,
)


@pytest.fixture
def telemetry_features():
    """Fixture providing train/test split feature sets from sample telemetry."""
    df = load_telemetry("data/sample_telemetry.csv")
    X, _ = split_features_and_labels(df)
    X_train, X_test = chronological_train_test_split(X, train_fraction=0.7)
    return X_train, X_test


def test_transform_before_fit_raises(telemetry_features):
    """Test calling transform or get_feature_names_out before fit raises NotFittedError."""
    X_train, _ = telemetry_features
    preprocessor = TelemetryPreprocessor()

    with pytest.raises(NotFittedError, match="must be fitted"):
        preprocessor.transform(X_train)

    with pytest.raises(NotFittedError, match="must be fitted"):
        preprocessor.get_feature_names_out()


def test_fit_learns_only_training_statistics(telemetry_features):
    """Test preprocessor learns statistics strictly from training partition."""
    X_train, X_test = telemetry_features
    preprocessor = TelemetryPreprocessor(scaler_type="standard")
    preprocessor.fit(X_train)

    assert preprocessor.fitted_ is True
    # Verify learned center matches training mean exactly, not test or global mean
    train_voltage_mean = float(X_train["solar_panel_voltage"].mean())
    test_voltage_mean = float(X_test["solar_panel_voltage"].mean())
    learned_center = preprocessor.learned_params_["solar_panel_voltage"]["center"]

    assert learned_center == pytest.approx(train_voltage_mean, rel=1e-5)
    assert learned_center != pytest.approx(test_voltage_mean, rel=1e-2)


def test_transform_preserves_rows_and_alignment(telemetry_features):
    """Test transformed output matches row counts and preserves original indexing."""
    X_train, X_test = telemetry_features
    preprocessor = TelemetryPreprocessor(
        add_rolling_stats=True,
        rolling_window=5,
        add_differencing=True,
    )
    X_train_trans = preprocessor.fit_transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    assert len(X_train_trans) == len(X_train)
    assert len(X_test_trans) == len(X_test)
    pd.testing.assert_index_equal(X_train_trans.index, X_train.index)
    pd.testing.assert_index_equal(X_test_trans.index, X_test.index)

    # Confirm no NaN values were introduced by rolling or differencing
    assert X_train_trans.isna().sum().sum() == 0
    assert X_test_trans.isna().sum().sum() == 0


def test_timestamp_preservation_option(telemetry_features):
    """Test timestamp column presence can be toggled via include_timestamp."""
    X_train, _ = telemetry_features
    preprocessor = TelemetryPreprocessor().fit(X_train)

    with_ts = preprocessor.transform(X_train, include_timestamp=True)
    assert "timestamp" in with_ts.columns

    without_ts = preprocessor.transform(X_train, include_timestamp=False)
    assert "timestamp" not in without_ts.columns


def test_backward_only_temporal_features():
    """Verify temporal rolling and differencing features never look ahead."""
    # Artificial sequence: 10, 20, 30, 40, 50
    toy_df = pd.DataFrame({
        "timestamp": [f"2026-10-01T00:0{i}:00Z" for i in range(5)],
        "val": [10.0, 20.0, 30.0, 40.0, 50.0],
    })
    preprocessor = TelemetryPreprocessor(
        scaler_type="none",  # keep raw values for easy assertions
        feature_cols=["val"],
        add_rolling_stats=True,
        rolling_window=3,
        add_differencing=True,
    )
    res = preprocessor.fit_transform(toy_df)

    # First row differencing must be 0.0 (no previous observation, zero rows lost)
    assert res.loc[0, "val_diff_1"] == 0.0
    # Second row differencing must be 20.0 - 10.0 = 10.0
    assert res.loc[1, "val_diff_1"] == 10.0

    # Rolling mean with window=3 and min_periods=1:
    # t=0: [10] -> mean = 10.0
    assert res.loc[0, "val_roll_mean_3"] == 10.0
    # t=1: [10, 20] -> mean = 15.0
    assert res.loc[1, "val_roll_mean_3"] == 15.0
    # t=2: [10, 20, 30] -> mean = 20.0
    assert res.loc[2, "val_roll_mean_3"] == 20.0
    # t=3: [20, 30, 40] -> mean = 30.0
    assert res.loc[3, "val_roll_mean_3"] == 30.0


def test_different_scaler_schemes(telemetry_features):
    """Test minmax, robust, and none normalization schemes."""
    X_train, _ = telemetry_features

    for scheme in ["minmax", "robust", "none"]:
        prep = TelemetryPreprocessor(scaler_type=scheme)
        out = prep.fit_transform(X_train, include_timestamp=False)
        assert len(out) == len(X_train)
        assert out.isna().sum().sum() == 0

    with pytest.raises(ValueError, match="Unsupported scaler_type"):
        TelemetryPreprocessor(scaler_type="invalid_scaler")


def test_input_immutability(telemetry_features):
    """Test that fitting and transforming never mutates input DataFrames."""
    X_train, _ = telemetry_features
    X_copy = X_train.copy(deep=True)

    prep = TelemetryPreprocessor(add_rolling_stats=True, add_differencing=True)
    prep.fit_transform(X_train)

    pd.testing.assert_frame_equal(X_train, X_copy)


def test_constant_channel_zero_division_guard():
    """Test that constant channel (zero variance) is handled without divide-by-zero NaN."""
    const_df = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
        "const_channel": [5.0, 5.0],
    })
    prep = TelemetryPreprocessor(scaler_type="standard")
    out = prep.fit_transform(const_df)
    assert not out["const_channel"].isna().any()
    assert not np.isinf(out["const_channel"]).any()

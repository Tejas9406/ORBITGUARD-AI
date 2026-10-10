"""Unit tests for ZScoreBaselineDetector."""

import numpy as np
import pandas as pd
import pytest

from src.data.loader import (
    chronological_train_test_split,
    load_telemetry,
    split_features_and_labels,
)
from src.models.base import ModelNotFittedError
from src.models.baseline_statistical import ZScoreBaselineDetector


@pytest.fixture
def split_data():
    """Fixture providing train/test split feature sets."""
    df = load_telemetry("data/sample_telemetry.csv")
    X, y = split_features_and_labels(df)
    X_train, X_test = chronological_train_test_split(X, train_fraction=0.7)
    y_train, y_test = chronological_train_test_split(y, train_fraction=0.7)
    return X_train, X_test, y_train, y_test


def test_baseline_unfitted_raises():
    """Verify calling methods before fit raises ModelNotFittedError."""
    detector = ZScoreBaselineDetector()
    df = pd.DataFrame({"timestamp": ["2026-10-01T00:00:00Z"], "voltage": [28.0]})

    with pytest.raises(ModelNotFittedError, match="must be fitted"):
        detector.score_samples(df)

    with pytest.raises(ModelNotFittedError, match="must be fitted"):
        detector.predict(df)

    with pytest.raises(ModelNotFittedError, match="must be fitted"):
        detector.explain(df)


def test_baseline_fit_learns_only_training_stats(split_data):
    """Verify detector parameters are computed solely from training partition."""
    X_train, X_test, _, _ = split_data
    detector = ZScoreBaselineDetector(threshold=3.0)
    detector.fit(X_train)

    assert detector.is_fitted_ is True
    # Confirm mean matches X_train mean, not X_test
    train_voltage_mean = float(X_train["solar_panel_voltage"].mean())
    test_voltage_mean = float(X_test["solar_panel_voltage"].mean())
    assert detector.means_["solar_panel_voltage"] == pytest.approx(train_voltage_mean, rel=1e-5)
    assert detector.means_["solar_panel_voltage"] != pytest.approx(test_voltage_mean, rel=1e-2)


def test_baseline_score_direction(split_data):
    """Verify continuous score direction: anomalous inputs receive higher scores than nominal."""
    X_train, _, _, _ = split_data
    detector = ZScoreBaselineDetector().fit(X_train)

    # Nominal point (close to training means)
    nominal_df = pd.DataFrame([{
        "timestamp": "2026-10-01T12:00:00Z",
        "solar_panel_voltage": detector.means_["solar_panel_voltage"],
        "battery_temp": detector.means_["battery_temp"],
        "battery_current": detector.means_["battery_current"],
        "gyro_x": detector.means_["gyro_x"],
        "gyro_y": detector.means_["gyro_y"],
        "gyro_z": detector.means_["gyro_z"],
    }])

    # Extreme anomalous point (massive temperature surge)
    anomalous_df = nominal_df.copy()
    anomalous_df["battery_temp"] = 120.0  # extreme surge

    nom_score = detector.score_samples(nominal_df)[0]
    anom_score = detector.score_samples(anomalous_df)[0]

    assert anom_score > nom_score
    assert nom_score < 0.1  # at mean, z-score is near zero
    assert anom_score > 10.0  # massive deviation


def test_baseline_nominal_eclipse_not_flagged(split_data):
    """Verify that expected orbital eclipse (low voltage ~0.1V) is NOT flagged as an anomaly."""
    X_train, _, _, _ = split_data
    detector = ZScoreBaselineDetector(threshold=3.0).fit(X_train)

    # Low voltage point representing standard eclipse
    eclipse_sample = pd.DataFrame([{
        "timestamp": "2026-10-01T01:30:00Z",
        "solar_panel_voltage": 0.1,  # normal eclipse voltage
        "battery_temp": 15.0,        # normal eclipse thermal
        "battery_current": -2.5,     # normal eclipse discharge
        "gyro_x": 0.0,
        "gyro_y": 0.0,
        "gyro_z": 0.067,
    }])

    score = detector.score_samples(eclipse_sample)[0]
    pred = detector.predict(eclipse_sample)[0]

    # Eclipse Z-score must stay well below 3-sigma
    assert score < 3.0
    assert pred == 0, "Normal eclipse was falsely flagged as an anomaly!"


def test_baseline_channel_attribution(split_data):
    """Verify explain identifies the specific telemetry channel triggering the alert."""
    X_train, _, _, _ = split_data
    detector = ZScoreBaselineDetector(threshold=3.0).fit(X_train)

    # Injected gyro spike point
    gyro_spike_df = pd.DataFrame([{
        "timestamp": "2026-10-01T15:00:00Z",
        "solar_panel_voltage": 28.0,
        "battery_temp": 20.0,
        "battery_current": 3.0,
        "gyro_x": 5.0,  # normal is ~0.00, std is 0.015 -> Z > 300!
        "gyro_y": 0.0,
        "gyro_z": 0.067,
    }])

    exp = detector.explain(gyro_spike_df)
    assert exp.loc[0, "is_anomaly"] == 1
    assert "gyro_x" in exp.loc[0, "triggered_channels"]
    assert exp.loc[0, "gyro_x_zscore"] > 50.0


def test_baseline_rejects_label_columns():
    """Verify passing ground-truth labels in feature matrix raises ValueError."""
    detector = ZScoreBaselineDetector()
    df_with_labels = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
        "voltage": [28.0, 28.1],
        "is_anomaly": [0, 1],
    })
    with pytest.raises(ValueError, match="Ground-truth label column"):
        detector.fit(df_with_labels)


def test_baseline_constant_channel_safety():
    """Verify constant channel (std=0) does not produce division-by-zero NaN or Inf."""
    const_df = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z", "2026-10-01T00:02:00Z"],
        "const_val": [5.0, 5.0, 5.0],
        "varying_val": [1.0, 2.0, 3.0],
    })
    detector = ZScoreBaselineDetector(threshold=3.0).fit(const_df)
    assert "const_val" in detector.constant_channels_

    scores = detector.score_samples(const_df)
    assert not np.isnan(scores).any()
    assert not np.isinf(scores).any()


def test_baseline_non_finite_values_raise(split_data):
    """Verify NaN or Inf in inference data raises ValueError."""
    X_train, _, _, _ = split_data
    detector = ZScoreBaselineDetector().fit(X_train)

    bad_df = X_train.iloc[:2].copy()
    bad_df.loc[bad_df.index[0], "solar_panel_voltage"] = np.nan
    with pytest.raises(ValueError, match="NaN/missing values"):
        detector.predict(bad_df)


def test_baseline_invalid_params_raise():
    """Verify invalid threshold or aggregation parameters raise ValueError."""
    with pytest.raises(ValueError, match="threshold must be positive"):
        ZScoreBaselineDetector(threshold=-1.0)

    with pytest.raises(ValueError, match="Unsupported aggregation"):
        ZScoreBaselineDetector(aggregation="invalid_agg")

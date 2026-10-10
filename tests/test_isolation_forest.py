"""Unit tests for IsolationForestDetector."""

import numpy as np
import pandas as pd
import pytest

from src.data.loader import (
    chronological_train_test_split,
    load_telemetry,
    split_features_and_labels,
)
from src.models.base import ModelNotFittedError
from src.models.isolation_forest import IsolationForestDetector


@pytest.fixture
def split_data():
    """Fixture providing train/test split feature and label sets."""
    df = load_telemetry("data/sample_telemetry.csv")
    X, y = split_features_and_labels(df)
    X_train, X_test = chronological_train_test_split(X, train_fraction=0.7)
    y_train, y_test = chronological_train_test_split(y, train_fraction=0.7)
    return X_train, X_test, y_train, y_test


def test_iforest_unfitted_raises():
    """Verify calling methods before fit raises ModelNotFittedError."""
    detector = IsolationForestDetector()
    df = pd.DataFrame({"timestamp": ["2026-10-01T00:00:00Z"], "val": [1.0]})

    with pytest.raises(ModelNotFittedError, match="must be fitted"):
        detector.score_samples(df)

    with pytest.raises(ModelNotFittedError, match="must be fitted"):
        detector.predict(df)

    with pytest.raises(ModelNotFittedError, match="must be fitted"):
        detector.explain(df)


def test_iforest_deterministic_with_fixed_seed(split_data):
    """Verify IsolationForestDetector produces perfectly deterministic outputs with fixed random_state."""
    X_train, X_test, _, _ = split_data
    clf1 = IsolationForestDetector(random_state=42).fit(X_train)
    clf2 = IsolationForestDetector(random_state=42).fit(X_train)

    scores1 = clf1.score_samples(X_test)
    scores2 = clf2.score_samples(X_test)
    np.testing.assert_allclose(scores1, scores2)

    pred1 = clf1.predict(X_test)
    pred2 = clf2.predict(X_test)
    np.testing.assert_array_equal(pred1, pred2)


def test_iforest_score_direction(split_data):
    """Verify continuous anomaly scores: higher score indicates higher anomaly likelihood."""
    X_train, _, _, _ = split_data
    detector = IsolationForestDetector(random_state=42).fit(X_train)

    nominal_obs = pd.DataFrame([{
        "timestamp": "2026-10-01T12:00:00Z",
        "solar_panel_voltage": detector.train_means_["solar_panel_voltage"],
        "battery_temp": detector.train_means_["battery_temp"],
        "battery_current": detector.train_means_["battery_current"],
        "gyro_x": detector.train_means_["gyro_x"],
        "gyro_y": detector.train_means_["gyro_y"],
        "gyro_z": detector.train_means_["gyro_z"],
    }])

    # Glitch with extreme values in multiple telemetry channels
    anomalous_obs = nominal_obs.copy()
    anomalous_obs["battery_temp"] = 85.0
    anomalous_obs["gyro_x"] = 5.0
    anomalous_obs["gyro_y"] = 5.0

    nom_score = detector.score_samples(nominal_obs)[0]
    anom_score = detector.score_samples(anomalous_obs)[0]

    assert anom_score > nom_score
    assert anom_score > detector.threshold_


def test_iforest_predictions_binary_and_aligns_with_threshold(split_data):
    """Verify predict returns binary 0/1 matching score > threshold_."""
    X_train, X_test, _, _ = split_data
    detector = IsolationForestDetector(random_state=42).fit(X_train)

    scores = detector.score_samples(X_test)
    preds = detector.predict(X_test)

    assert set(np.unique(preds)).issubset({0, 1})
    expected_preds = (scores > detector.threshold_).astype(int)
    np.testing.assert_array_equal(preds, expected_preds)


def test_iforest_rejects_label_columns():
    """Verify passing ground-truth labels in feature matrix raises ValueError."""
    detector = IsolationForestDetector()
    df_with_labels = pd.DataFrame({
        "timestamp": ["2026-10-01T00:00:00Z", "2026-10-01T00:01:00Z"],
        "voltage": [28.0, 28.1],
        "is_anomaly": [0, 1],
    })
    with pytest.raises(ValueError, match="Ground-truth label column"):
        detector.fit(df_with_labels)


def test_iforest_preserves_row_order_and_index(split_data):
    """Verify output arrays and explanation DataFrames match input row indexing exactly."""
    X_train, X_test, _, _ = split_data
    detector = IsolationForestDetector(random_state=42).fit(X_train)

    scores = detector.score_samples(X_test)
    preds = detector.predict(X_test)
    exp = detector.explain(X_test)

    assert len(scores) == len(X_test)
    assert len(preds) == len(X_test)
    assert len(exp) == len(X_test)
    pd.testing.assert_index_equal(exp.index, X_test.index)


def test_iforest_detects_injected_glitches_in_test_set(split_data):
    """Verify detector triggers alerts on injected gyroscope glitches in the test split."""
    X_train, X_test, _, y_test = split_data
    detector = IsolationForestDetector(contamination=0.04, random_state=42).fit(X_train)

    preds = detector.predict(X_test)
    # The gyro_glitch injected in test set at minutes 1100-1120
    gyro_glitch_mask = (y_test["anomaly_type"] == "gyro_glitch").to_numpy()
    assert gyro_glitch_mask.sum() == 21

    # Ensure detector catches the overwhelming majority of gyro glitch points
    glitch_recall = preds[gyro_glitch_mask].mean()
    assert glitch_recall > 0.80, f"Expected >80% recall on severe gyro glitches, got {glitch_recall:.2f}"


def test_iforest_explain_attribution(split_data):
    """Verify explain returns top contributing channels."""
    X_train, X_test, _, _ = split_data
    detector = IsolationForestDetector(random_state=42).fit(X_train)

    exp = detector.explain(X_test.iloc[:5], top_k_channels=2)
    assert "top_contributing_channels" in exp.columns
    assert "anomaly_score" in exp.columns
    assert "is_anomaly" in exp.columns


def test_iforest_invalid_parameters():
    """Verify invalid contamination and n_estimators raise ValueError."""
    with pytest.raises(ValueError, match="contamination must be"):
        IsolationForestDetector(contamination=0.8)

    with pytest.raises(ValueError, match="contamination must be"):
        IsolationForestDetector(contamination=-0.1)

    with pytest.raises(ValueError, match="n_estimators must be at least 1"):
        IsolationForestDetector(n_estimators=0)

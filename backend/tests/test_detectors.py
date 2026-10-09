import numpy as np
import pytest
from backend.detectors.zscore import detect_zscore
from backend.detectors.isoforest import detect_isoforest

def test_zscore_nominal():
    # Gaussian noise with mean 0, std 1
    np.random.seed(42)
    nominal_signal = np.random.normal(0, 0.1, 200)
    anomalies = detect_zscore(nominal_signal, win=50, z_threshold=3.5)
    # Shouldn't flag random noise below 3.5 sigma
    assert len(anomalies) == 0

def test_zscore_with_injected_spike():
    np.random.seed(42)
    signal = np.random.normal(0, 0.1, 200)
    # Inject spike at indices 120-125
    signal[120:126] = 5.0
    anomalies = detect_zscore(signal, win=50, z_threshold=3.0)
    assert len(anomalies) >= 1
    # Check that anomaly window captures the spike onset
    first = anomalies[0]
    assert first["start_step"] <= 122
    assert first["end_step"] >= 122
    assert first["severity"] == "critical"
    assert "evidence" in first
    assert first["evidence"]["observed_peak"] >= 4.5

def test_zscore_constant_signal_zero_division():
    # Signal with zero variance
    flat_signal = np.zeros(100)
    anomalies = detect_zscore(flat_signal, win=30, z_threshold=3.0)
    # Must not raise ZeroDivisionError or crash
    assert len(anomalies) == 0

def test_isoforest_detection():
    np.random.seed(42)
    signal = np.sin(np.linspace(0, 20, 300))
    # Inject wild erratic noise at indices 150-160
    signal[150:161] = np.random.uniform(5.0, 8.0, 11)
    anomalies = detect_isoforest(signal, contamination=0.03, n_estimators=50)
    assert len(anomalies) >= 1
    found = any(148 <= a["start_step"] <= 165 for a in anomalies)
    assert found

"""Deterministic, explainable features for telemetry anomaly processing."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_features(values: np.ndarray, window: int = 100) -> pd.DataFrame:
    """Create causal features; each baseline at time t uses only earlier data."""
    if values.ndim != 1:
        raise ValueError("build_features expects a one-dimensional target signal")
    if window < 20:
        raise ValueError("window must be at least 20 samples")
    series = pd.Series(values, dtype="float64")
    history = series.shift(1)
    minimum = max(20, window // 3)
    median = history.rolling(window, min_periods=minimum).median()
    mad = (history - median).abs().rolling(window, min_periods=minimum).median()
    safe_mad = mad.mask(mad < 1e-9, 1e-9)
    robust_z = (0.6745 * (series - median).abs() / safe_mad).fillna(0).clip(upper=50)
    return pd.DataFrame({
        "time_step": np.arange(len(values), dtype=np.int64),
        "value": series,
        "delta": series.diff().fillna(0),
        "rolling_median": median,
        "rolling_mad": mad,
        "rolling_mean": history.rolling(window, min_periods=minimum).mean(),
        "rolling_std": history.rolling(window, min_periods=minimum).std().fillna(0),
        "robust_zscore": robust_z,
    })

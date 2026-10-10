"""Pure-NumPy fresh inference engine using pretrained Telemanom Keras LSTM weights.

Loads .h5 weights via h5py and executes the exact Keras LSTM forward pass
without requiring legacy TensorFlow or Keras runtime dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import h5py
import numpy as np
import pandas as pd

from .events import group_events

logger = logging.getLogger("orbitguard.lstm")


def hard_sigmoid(x: np.ndarray) -> np.ndarray:
    """Keras default hard_sigmoid activation."""
    return np.clip(0.2 * x + 0.5, 0.0, 1.0)


def load_lstm_weights(model_path: str | Path) -> dict[str, np.ndarray]:
    """Extract layer weights from a Telemanom Keras .h5 model file."""
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Pretrained model weight file not found: {path}")

    with h5py.File(path, "r") as f:
        w = f["model_weights"]
        weights = {
            "W1": w["lstm_1"]["lstm_1"]["kernel:0"][:],
            "U1": w["lstm_1"]["lstm_1"]["recurrent_kernel:0"][:],
            "b1": w["lstm_1"]["lstm_1"]["bias:0"][:],
            "W2": w["lstm_2"]["lstm_2"]["kernel:0"][:],
            "U2": w["lstm_2"]["lstm_2"]["recurrent_kernel:0"][:],
            "b2": w["lstm_2"]["lstm_2"]["bias:0"][:],
            "W_dense": w["dense_1"]["dense_1"]["kernel:0"][:],
            "b_dense": w["dense_1"]["dense_1"]["bias:0"][:],
        }
    return weights


def shape_lstm_input(
    raw_telemetry: np.ndarray,
    l_s: int = 250,
    n_predictions: int = 10,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """Shape continuous telemetry matrix into (N, l_s, features) windows."""
    if raw_telemetry.ndim != 2:
        raise ValueError(
            f"LSTM requires 2D telemetry array of shape (samples, features). Received ndim={raw_telemetry.ndim}"
        )

    num_samples = len(raw_telemetry)
    total_window = l_s + n_predictions
    if num_samples <= total_window:
        raise ValueError(
            f"Telemetry length ({num_samples}) too short for window {total_window} (l_s={l_s} + n_predictions={n_predictions})"
        )

    n_windows = num_samples - total_window
    windows = []
    for i in range(n_windows):
        windows.append(raw_telemetry[i : i + total_window])
    data = np.asarray(windows, dtype=np.float32)

    X = data[:, :-n_predictions, :]
    # Target signal is at channel index 0 (NASA standard)
    y = data[:, -n_predictions:, 0]
    offset = total_window
    return X, y, offset


def run_lstm_forward(
    X: np.ndarray,
    weights: dict[str, np.ndarray],
    batch_size: int = 256,
) -> np.ndarray:
    """Execute vectorized forward pass through 2-layer LSTM + Dense head."""
    W1, U1, b1 = weights["W1"], weights["U1"], weights["b1"]
    W2, U2, b2 = weights["W2"], weights["U2"], weights["b2"]
    W_dense, b_dense = weights["W_dense"], weights["b_dense"]

    n_samples, timesteps, feat_dim = X.shape
    if feat_dim != W1.shape[0]:
        raise ValueError(
            f"Feature dimension mismatch: input has {feat_dim} features, but LSTM model expects {W1.shape[0]} features."
        )

    units = U1.shape[0]  # 80
    predictions = []

    for start_idx in range(0, n_samples, batch_size):
        batch = X[start_idx : start_idx + batch_size]
        B = batch.shape[0]

        # Pre-multiply input by W1 across all time steps
        xW1 = np.dot(batch, W1)  # (B, timesteps, 4*units)
        h1 = np.zeros((B, units), dtype=np.float32)
        c1 = np.zeros((B, units), dtype=np.float32)
        h1_seq = np.zeros((B, timesteps, units), dtype=np.float32)

        for t in range(timesteps):
            z = xW1[:, t, :] + np.dot(h1, U1) + b1
            zi = hard_sigmoid(z[:, :units])
            zf = hard_sigmoid(z[:, units : 2 * units])
            zc = np.tanh(z[:, 2 * units : 3 * units])
            zo = hard_sigmoid(z[:, 3 * units :])
            c1 = zf * c1 + zi * zc
            h1 = zo * np.tanh(c1)
            h1_seq[:, t, :] = h1

        # Layer 2: LSTM with return_sequences=False
        xW2 = np.dot(h1_seq, W2)  # (B, timesteps, 4*units)
        h2 = np.zeros((B, units), dtype=np.float32)
        c2 = np.zeros((B, units), dtype=np.float32)

        for t in range(timesteps):
            z = xW2[:, t, :] + np.dot(h2, U2) + b2
            zi = hard_sigmoid(z[:, :units])
            zf = hard_sigmoid(z[:, units : 2 * units])
            zc = np.tanh(z[:, 2 * units : 3 * units])
            zo = hard_sigmoid(z[:, 3 * units :])
            c2 = zf * c2 + zi * zc
            h2 = zo * np.tanh(c2)

        # Dense readout (B, n_predictions)
        y_batch = np.dot(h2, W_dense) + b_dense
        # Telemanom 'first' step ahead prediction
        predictions.append(y_batch[:, 0])

    return np.concatenate(predictions, axis=0)


def compute_prediction_errors(
    y_hat: np.ndarray,
    y_test: np.ndarray,
    smoothing_window: int = 105,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute point-level raw errors and EWMA smoothed error sequence."""
    raw_error = np.abs(y_hat - y_test[:, 0])
    series = pd.Series(raw_error, dtype=np.float64)
    smoothed = series.ewm(span=smoothing_window).mean().to_numpy()
    return raw_error, smoothed


def detect_lstm_anomalies(
    smoothed_error: np.ndarray,
    threshold_sigma: float = 3.5,
    window_warmup: int = 100,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """Generate normalized anomaly scores from smoothed prediction errors and group events."""
    if len(smoothed_error) == 0:
        return np.array([]), pd.DataFrame(columns=["start", "end", "flagged_points", "peak_score", "severity"])

    baseline_mean = np.mean(smoothed_error[: min(len(smoothed_error), window_warmup)])
    baseline_std = np.std(smoothed_error[: min(len(smoothed_error), window_warmup)])
    safe_std = max(float(baseline_std), 1e-6)

    # Standardized error score
    scores = (smoothed_error - baseline_mean) / safe_std
    scores = np.clip(scores, 0.0, 50.0)

    events = group_events(scores, threshold=threshold_sigma, max_gap=5, min_points=3)
    return scores, events

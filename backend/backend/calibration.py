"""Data-Driven Threshold Calibration for OrbitGuard AI.

Replaces hardcoded threshold=3.5 with calibrated, evidence-based thresholds
derived from actual training data distributions.

Calibration strategies:
1. Statistical Detector: Fit training Z-score distribution, set threshold at
   configurable percentile (default 99th) of normal training scores.
2. Isolation Forest: Use training-fitted anomaly scores, calibrate at
   99th percentile (already in isolation_forest.py calibrated_threshold).
3. LSTM: Calibrate from training prediction errors baseline statistics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .features import build_features

logger = logging.getLogger("orbitguard.calibration")


@dataclass
class CalibratedThreshold:
    """Result of data-driven threshold calibration."""
    detector: str
    method: str                  # e.g., "percentile_99", "mad_sigma", "iqr_fence"
    threshold_value: float
    training_mean: float
    training_std: float
    training_median: float
    training_p95: float
    training_p99: float
    n_training_samples: int
    fallback_used: bool          # True if calibration failed and default was used


def calibrate_statistical_threshold(
    train_signal: np.ndarray,
    window: int = 100,
    percentile: float = 99.0,
    min_threshold: float = 2.0,
    max_threshold: float = 15.0,
) -> CalibratedThreshold:
    """Calibrate the statistical detector threshold from training data Z-score distribution.

    Runs the same build_features pipeline on training data to establish the
    normal-behavior Z-score distribution, then sets the threshold at the
    specified percentile. This avoids the arbitrary fixed 3.5.

    Args:
        train_signal: 1D training time series (known-normal data).
        window: Rolling window size (same as will be used on test data).
        percentile: Percentile of training Z-scores to use as threshold.
        min_threshold: Floor for the threshold to prevent over-sensitivity.
        max_threshold: Ceiling to prevent under-sensitivity.

    Returns:
        CalibratedThreshold with the data-derived threshold value.
    """
    fallback = False
    try:
        if len(train_signal) < 40:
            raise ValueError(f"Training signal too short ({len(train_signal)}) for calibration")

        features = build_features(train_signal, window=max(20, min(window, len(train_signal))))
        scores = features["robust_zscore"].to_numpy()

        # Remove warm-up NaN/zero region
        valid = scores[scores > 0]
        if len(valid) < 20:
            # Fall back to full scores including zeros
            valid = scores[~np.isnan(scores)]

        if len(valid) < 10:
            raise ValueError("Insufficient valid training scores for calibration")

        t_mean = float(np.mean(valid))
        t_std = float(np.std(valid))
        t_median = float(np.median(valid))
        t_p95 = float(np.percentile(valid, 95.0))
        t_p99 = float(np.percentile(valid, min(percentile, 99.9)))

        # Primary: percentile-based threshold
        threshold = t_p99

        # Apply bounds
        threshold = float(np.clip(threshold, min_threshold, max_threshold))

        return CalibratedThreshold(
            detector="Statistical Baseline",
            method=f"percentile_{percentile:.0f}",
            threshold_value=round(threshold, 4),
            training_mean=round(t_mean, 4),
            training_std=round(t_std, 4),
            training_median=round(t_median, 4),
            training_p95=round(t_p95, 4),
            training_p99=round(t_p99, 4),
            n_training_samples=len(valid),
            fallback_used=False,
        )
    except Exception as exc:
        logger.warning(f"Statistical threshold calibration failed: {exc}. Using default 3.5.")
        fallback = True
        return CalibratedThreshold(
            detector="Statistical Baseline",
            method="fallback_default",
            threshold_value=3.5,
            training_mean=0.0,
            training_std=0.0,
            training_median=0.0,
            training_p95=0.0,
            training_p99=0.0,
            n_training_samples=0,
            fallback_used=True,
        )


def calibrate_lstm_threshold(
    smoothed_errors: np.ndarray,
    percentile: float = 99.0,
    sigma_multiplier: float = 3.0,
    min_threshold: float = 1.5,
    max_threshold: float = 12.0,
) -> CalibratedThreshold:
    """Calibrate LSTM anomaly detection threshold from smoothed error distribution.

    Uses the early portion of smoothed errors (assumed normal) to establish baseline,
    then sets threshold via percentile or sigma method.

    Args:
        smoothed_errors: EWMA-smoothed prediction error sequence.
        percentile: Percentile for threshold calibration.
        sigma_multiplier: Alternative sigma-based threshold (mean + k*sigma).
        min_threshold: Floor.
        max_threshold: Ceiling.
    """
    try:
        if len(smoothed_errors) < 20:
            raise ValueError("Insufficient smoothed errors for calibration")

        # Use first 30% as calibration baseline (early data typically normal)
        warmup_n = max(20, len(smoothed_errors) // 3)
        baseline = smoothed_errors[:warmup_n]

        b_mean = float(np.mean(baseline))
        b_std = float(np.std(baseline))
        safe_std = max(b_std, 1e-6)

        # Standardize full error sequence
        standardized = (smoothed_errors - b_mean) / safe_std
        standardized = np.clip(standardized, 0.0, 50.0)

        # Threshold from training baseline
        baseline_std_scores = (baseline - b_mean) / safe_std
        baseline_std_scores = np.clip(baseline_std_scores, 0.0, 50.0)

        p_threshold = float(np.percentile(baseline_std_scores, min(percentile, 99.9)))
        s_threshold = sigma_multiplier

        # Use the more conservative (higher) threshold
        threshold = max(p_threshold, s_threshold)
        threshold = float(np.clip(threshold, min_threshold, max_threshold))

        return CalibratedThreshold(
            detector="Pretrained LSTM",
            method=f"max(percentile_{percentile:.0f}, {sigma_multiplier:.1f}sigma)",
            threshold_value=round(threshold, 4),
            training_mean=round(b_mean, 6),
            training_std=round(safe_std, 6),
            training_median=round(float(np.median(baseline)), 6),
            training_p95=round(float(np.percentile(baseline_std_scores, 95.0)), 4),
            training_p99=round(float(np.percentile(baseline_std_scores, 99.0)), 4),
            n_training_samples=len(baseline),
            fallback_used=False,
        )
    except Exception as exc:
        logger.warning(f"LSTM threshold calibration failed: {exc}. Using default 3.0.")
        return CalibratedThreshold(
            detector="Pretrained LSTM",
            method="fallback_default",
            threshold_value=3.0,
            training_mean=0.0,
            training_std=0.0,
            training_median=0.0,
            training_p95=0.0,
            training_p99=0.0,
            n_training_samples=0,
            fallback_used=True,
        )


def calibrate_all_thresholds(
    train_signal: Optional[np.ndarray] = None,
    smoothed_errors: Optional[np.ndarray] = None,
    window: int = 100,
    stat_percentile: float = 99.0,
    lstm_percentile: float = 99.0,
    lstm_sigma: float = 3.0,
) -> dict[str, CalibratedThreshold]:
    """Calibrate thresholds for all available detectors.

    Returns dict keyed by detector name.
    """
    results = {}

    if train_signal is not None:
        results["statistical"] = calibrate_statistical_threshold(
            train_signal, window=window, percentile=stat_percentile
        )

    if smoothed_errors is not None:
        results["lstm"] = calibrate_lstm_threshold(
            smoothed_errors, percentile=lstm_percentile, sigma_multiplier=lstm_sigma
        )

    return results

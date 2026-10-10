"""Isolation Forest detector implementation for satellite telemetry anomaly detection.

Features:
- Pure-NumPy implementation of Isolation Forest (Liu, Ting, Zhou 2008),
  ensuring full resilience against environments where C-extension DLLs
  (like scipy/sklearn compiled modules) are restricted by security policies.
- Prevents test-data leakage by fitting strictly on normal historical training data.
- Does not use ground-truth labels for training (strictly unsupervised).
- Supports both multivariate telemetry matrices (NASA 25/55 channel models)
  and univariate temporal streams via causal feature expansion.
- Produces traceable anomaly scores, calibrated alert thresholds, and grouped event intervals.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .events import group_events

logger = logging.getLogger("orbitguard.isolation_forest")


def c_factor(n: int) -> float:
    """Average path length of unsuccessful search in Binary Search Tree (BST)."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    return 2.0 * (np.log(n - 1) + 0.5772156649) - (2.0 * (n - 1) / n)


class IsolationTree:
    """Single isolation tree in the ensemble."""

    def __init__(self, height_limit: int):
        self.height_limit = height_limit
        self.left: Optional[IsolationTree] = None
        self.right: Optional[IsolationTree] = None
        self.split_feat: Optional[int] = None
        self.split_val: Optional[float] = None
        self.size: int = 0
        self.is_leaf: bool = False

    def fit(self, X: np.ndarray, current_height: int = 0) -> IsolationTree:
        self.size = X.shape[0]
        if current_height >= self.height_limit or self.size <= 1:
            self.is_leaf = True
            return self

        feat_mins = np.min(X, axis=0)
        feat_maxs = np.max(X, axis=0)
        valid_feats = np.where(feat_maxs > feat_mins)[0]
        if len(valid_feats) == 0:
            self.is_leaf = True
            return self

        self.split_feat = int(np.random.choice(valid_feats))
        f_min = float(feat_mins[self.split_feat])
        f_max = float(feat_maxs[self.split_feat])
        self.split_val = float(np.random.uniform(f_min, f_max))

        left_mask = X[:, self.split_feat] < self.split_val
        self.left = IsolationTree(self.height_limit).fit(X[left_mask], current_height + 1)
        self.right = IsolationTree(self.height_limit).fit(X[~left_mask], current_height + 1)
        return self

    def path_length(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        lengths = np.zeros(n, dtype=np.float64)
        if self.is_leaf or self.split_feat is None or self.split_val is None:
            return np.full(n, c_factor(self.size))

        left_mask = X[:, self.split_feat] < self.split_val
        if np.any(left_mask) and self.left is not None:
            lengths[left_mask] = 1.0 + self.left.path_length(X[left_mask])
        if np.any(~left_mask) and self.right is not None:
            lengths[~left_mask] = 1.0 + self.right.path_length(X[~left_mask])
        return lengths


class TelemetryIsolationForest:
    """Ensemble of Isolation Trees fitted strictly on training telemetry."""

    def __init__(self, n_estimators: int = 100, max_samples: int = 256, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        self.trees: list[IsolationTree] = []
        self.c_sub: float = 1.0
        self.train_score_mean: float = 0.5
        self.train_score_std: float = 0.1
        self.calibrated_threshold: float = 3.5

    def fit(self, X_train: np.ndarray) -> TelemetryIsolationForest:
        """Fit Isolation Forest strictly on normal training data (zero label leakage)."""
        rng = np.random.RandomState(self.random_state)
        n = X_train.shape[0]
        sub_size = min(self.max_samples, n)
        self.c_sub = c_factor(sub_size)
        height_limit = int(np.ceil(np.log2(max(sub_size, 2))))

        self.trees = []
        for _ in range(self.n_estimators):
            idx = rng.choice(n, size=sub_size, replace=False)
            tree = IsolationTree(height_limit).fit(X_train[idx])
            self.trees.append(tree)

        # Baseline evaluation on training set for score calibration
        train_raw_scores = self.score_raw(X_train)
        self.train_score_mean = float(np.mean(train_raw_scores))
        self.train_score_std = float(max(np.std(train_raw_scores), 1e-4))
        # 99th percentile or mean + 3 sigma of normal training scores
        threshold_val = float(np.percentile(train_raw_scores, 99.0))
        self.calibrated_threshold = max(3.0, (threshold_val - self.train_score_mean) / self.train_score_std)
        return self

    def score_raw(self, X: np.ndarray) -> np.ndarray:
        """Raw anomaly score s in [0, 1] where s > 0.5 indicates anomalous points."""
        paths = np.array([tree.path_length(X) for tree in self.trees])
        mean_paths = np.mean(paths, axis=0)
        return 2.0 ** (-mean_paths / max(self.c_sub, 1e-6))

    def score_standardized(self, X: np.ndarray) -> np.ndarray:
        """Standardized deviation score against training distribution baseline."""
        raw = self.score_raw(X)
        z = (raw - self.train_score_mean) / self.train_score_std
        return np.clip(z, 0.0, 50.0)


def extract_univariate_tabular_features(series: np.ndarray, window: int = 20) -> np.ndarray:
    """Convert 1D temporal series into causal multi-dimensional feature space for tree isolation."""
    arr_1d = series.ravel() if isinstance(series, np.ndarray) else np.asarray(series).ravel()
    s = pd.Series(arr_1d, dtype=np.float64)
    df = pd.DataFrame({
        "val": s,
        "lag1": s.shift(1).bfill(),
        "lag2": s.shift(2).bfill(),
        "delta": s.diff().fillna(0),
        "roll_mean": s.rolling(window, min_periods=5).mean().bfill(),
        "roll_std": s.rolling(window, min_periods=5).std().fillna(0),
    })
    return df.to_numpy(dtype=np.float32)


def run_isolation_forest_detection(
    train_telemetry: np.ndarray,
    test_telemetry: np.ndarray,
    threshold: float = 3.5,
    random_state: int = 42,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """Train Isolation Forest on normal training telemetry and evaluate on held-out test data.

    Returns:
        calibrated_scores: 1D standardized anomaly scores on test sequence
        events: DataFrame of grouped anomaly incident windows
    """
    if train_telemetry.ndim == 1:
        X_train = extract_univariate_tabular_features(train_telemetry)
        X_test = extract_univariate_tabular_features(test_telemetry)
    else:
        X_train = train_telemetry
        X_test = test_telemetry

    forest = TelemetryIsolationForest(n_estimators=100, max_samples=256, random_state=random_state)
    forest.fit(X_train)

    test_scores = forest.score_standardized(X_test)
    effective_thresh = max(threshold, 2.5)
    events = group_events(test_scores, threshold=effective_thresh, max_gap=5, min_points=3)
    return test_scores, events

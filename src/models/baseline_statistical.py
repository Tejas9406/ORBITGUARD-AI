"""Statistical baseline anomaly detector for OrbitGuard AI.

Implements a transparent, channel-level Z-score anomaly detector that learns
nominal channel means and standard deviations strictly from training data.
Provides per-channel attribution to explain which telemetry sensors triggered alerts.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.models.base import BaseDetector, ModelNotFittedError


class ZScoreBaselineDetector(BaseDetector):
    """Channel-wise Z-score statistical baseline anomaly detector.

    Learns the nominal mean and standard deviation for each telemetry channel
    strictly from training observations. At inference time, computes the absolute
    Z-score for each channel:

        Z_{i, c} = |x_{i, c} - mu_c| / sigma_c

    The overall observation anomaly score is the aggregated channel deviation
    (default: maximum absolute Z-score across channels). An alert is triggered
    when the score exceeds the configurable threshold (default: 3.0 sigma).

    Attributes:
        threshold: Z-score cutoff for flagging an anomaly. Defaults to 3.0.
        aggregation: Strategy to combine channel Z-scores ("max", "mean", "euclidean").
            Defaults to "max" for transparent worst-case channel attribution.
        timestamp_col: Name of timestamp column to exclude from calculation.
    """

    def __init__(
        self,
        threshold: float = 3.0,
        aggregation: str = "max",
        timestamp_col: str = "timestamp",
    ):
        super().__init__(timestamp_col=timestamp_col)
        if threshold <= 0:
            raise ValueError(f"threshold must be positive, got {threshold}.")
        if aggregation not in {"max", "mean", "euclidean"}:
            raise ValueError(f"Unsupported aggregation '{aggregation}'. Choose from 'max', 'mean', 'euclidean'.")

        self.threshold = float(threshold)
        self.aggregation = aggregation
        self.means_: Dict[str, float] = {}
        self.stds_: Dict[str, float] = {}
        self.constant_channels_: List[str] = []

    def fit(self, X: pd.DataFrame) -> "ZScoreBaselineDetector":
        """Computes channel means and standard deviations strictly on training telemetry.

        Args:
            X: Training DataFrame containing telemetry features.

        Returns:
            self: Fitted detector instance.

        Raises:
            ValueError: If X has fewer than 2 rows, is empty, or contains label columns.
        """
        X_numeric, _ = self._extract_numeric_features(X, enforce_fitted_features=False)

        if len(X_numeric) < 2:
            raise ValueError(f"Training dataset must have at least 2 observations to compute variance, got {len(X_numeric)}.")

        self.feature_names_ = list(X_numeric.columns)
        self.means_ = {}
        self.stds_ = {}
        self.constant_channels_ = []

        for col in self.feature_names_:
            col_series = X_numeric[col].astype(float)
            mean_val = float(col_series.mean())
            std_val = float(col_series.std(ddof=1))

            self.means_[col] = mean_val
            # Safe handling for constant or near-constant telemetry channels
            if std_val < 1e-8 or np.isnan(std_val):
                self.stds_[col] = 1.0
                self.constant_channels_.append(col)
            else:
                self.stds_[col] = std_val

        self.is_fitted_ = True
        return self

    def _compute_channel_zscores(self, X_numeric: pd.DataFrame) -> pd.DataFrame:
        """Internal helper computing absolute Z-scores per channel."""
        z_df = pd.DataFrame(index=X_numeric.index)
        for col in self.feature_names_:
            mu = self.means_[col]
            sigma = self.stds_[col]
            z_df[f"{col}_zscore"] = np.abs(X_numeric[col].astype(float) - mu) / sigma
        return z_df

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Computes continuous anomaly score for each observation.

        Score Direction: Higher score = more anomalous.

        Args:
            X: Telemetry DataFrame.

        Returns:
            np.ndarray: 1D array of float anomaly scores.

        Raises:
            ModelNotFittedError: If model is not fitted.
        """
        if not self.is_fitted_:
            raise ModelNotFittedError("ZScoreBaselineDetector must be fitted before calling score_samples.")

        X_numeric, _ = self._extract_numeric_features(X, enforce_fitted_features=True)
        z_df = self._compute_channel_zscores(X_numeric)

        if self.aggregation == "max":
            scores = z_df.max(axis=1).to_numpy()
        elif self.aggregation == "mean":
            scores = z_df.mean(axis=1).to_numpy()
        elif self.aggregation == "euclidean":
            scores = np.sqrt((z_df ** 2).sum(axis=1)).to_numpy()

        return scores

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts binary anomaly labels (1 = anomaly, 0 = nominal).

        Args:
            X: Telemetry DataFrame.

        Returns:
            np.ndarray: 1D integer array (0 or 1).
        """
        scores = self.score_samples(X)
        return (scores > self.threshold).astype(int)

    def explain(self, X: pd.DataFrame) -> pd.DataFrame:
        """Generates detailed channel-level anomaly attribution diagnostics.

        Args:
            X: Telemetry DataFrame.

        Returns:
            pd.DataFrame: Contains per-channel Z-scores, overall score, binary prediction,
                and a list of telemetry channels that exceeded the anomaly threshold.
        """
        if not self.is_fitted_:
            raise ModelNotFittedError("ZScoreBaselineDetector must be fitted before calling explain.")

        X_numeric, original_index = self._extract_numeric_features(X, enforce_fitted_features=True)
        z_df = self._compute_channel_zscores(X_numeric)
        scores = self.score_samples(X)
        predictions = (scores > self.threshold).astype(int)

        # Identify which specific channels breached the threshold for each row
        triggered_list = []
        for idx in z_df.index:
            row_z = z_df.loc[idx]
            breached = [
                col.replace("_zscore", "")
                for col in z_df.columns
                if row_z[col] > self.threshold
            ]
            triggered_list.append(", ".join(breached) if breached else "none")

        explanation_df = z_df.copy()
        explanation_df["anomaly_score"] = scores
        explanation_df["is_anomaly"] = predictions
        explanation_df["triggered_channels"] = triggered_list
        explanation_df.index = original_index

        return explanation_df

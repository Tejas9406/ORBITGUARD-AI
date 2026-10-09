"""Scikit-learn Isolation Forest anomaly detector for OrbitGuard AI.

Wraps scikit-learn's IsolationForest with OrbitGuard's BaseDetector interface:
- Score Convention: Higher score indicates higher likelihood of anomaly.
- Prediction Convention: 1 = Anomaly, 0 = Nominal.
- Leakage Prevention: Fits strictly on training telemetry features without label inputs.
- Timestamp & Index Alignment: Preserves input DataFrame index and orders.
"""

from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.models.base import BaseDetector, ModelNotFittedError


class IsolationForestDetector(BaseDetector):
    """Isolation Forest anomaly detector for multi-channel satellite telemetry.

    Builds an ensemble of isolation trees to identify multivariate outliers
    based on path lengths in feature space.

    Score Direction Guarantee:
    - Scikit-learn's native `score_samples` produces more negative values for anomalies.
    - This wrapper inverts the score: `score = -model.score_samples(X)`, ensuring that
      higher continuous scores strictly represent higher anomaly severity.
    - Decision threshold: `threshold_ = -model.offset_`. An observation is flagged
      as an anomaly (`predict=1`) when `score > threshold_`.

    Attributes:
        contamination: Estimated proportion of outliers in the dataset.
            Must be in (0, 0.5] or "auto". Defaults to 0.04.
        n_estimators: Number of isolation trees in the ensemble. Defaults to 100.
        max_samples: Number of samples to draw from X to train each tree. Defaults to "auto".
        random_state: Seed for pseudo-random number generator. Defaults to 42 for determinism.
        timestamp_col: Name of timestamp column to exclude from model inputs.
    """

    def __init__(
        self,
        contamination: Union[float, str] = 0.04,
        n_estimators: int = 100,
        max_samples: Union[int, float, str] = "auto",
        random_state: int = 42,
        timestamp_col: str = "timestamp",
    ):
        super().__init__(timestamp_col=timestamp_col)
        if isinstance(contamination, (int, float)):
            if not (0.0 < float(contamination) <= 0.5):
                raise ValueError(f"contamination must be in (0, 0.5] or 'auto', got {contamination}.")
        elif contamination != "auto":
            raise ValueError(f"contamination must be a float in (0, 0.5] or 'auto', got '{contamination}'.")

        if n_estimators < 1:
            raise ValueError(f"n_estimators must be at least 1, got {n_estimators}.")

        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state

        self.model_: Optional[IsolationForest] = None
        self.threshold_: Optional[float] = None
        self.train_means_: Dict[str, float] = {}
        self.train_stds_: Dict[str, float] = {}

    def fit(self, X: pd.DataFrame) -> "IsolationForestDetector":
        """Fits the Isolation Forest strictly on training telemetry observations.

        Args:
            X: Training DataFrame containing telemetry features.

        Returns:
            self: Fitted detector instance.

        Raises:
            ValueError: If X has fewer than 2 rows, is empty, or contains label columns.
        """
        X_numeric, _ = self._extract_numeric_features(X, enforce_fitted_features=False)

        if len(X_numeric) < 2:
            raise ValueError(f"Training dataset must have at least 2 observations to fit trees, got {len(X_numeric)}.")

        self.feature_names_ = list(X_numeric.columns)

        # Store training baseline distributions for explanation/attribution
        self.train_means_ = {}
        self.train_stds_ = {}
        for col in self.feature_names_:
            col_series = X_numeric[col].astype(float)
            std_val = float(col_series.std(ddof=1))
            self.train_means_[col] = float(col_series.mean())
            self.train_stds_[col] = std_val if (std_val > 1e-8 and not np.isnan(std_val)) else 1.0

        # Initialize scikit-learn IsolationForest
        self.model_ = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            random_state=self.random_state,
        )

        self.model_.fit(X_numeric)
        # Invert offset to match inverted score convention (score > threshold_ => anomaly)
        self.threshold_ = float(-self.model_.offset_)
        self.is_fitted_ = True

        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Computes continuous anomaly score for each observation.

        Convention: Higher score strictly indicates higher anomaly severity.

        Args:
            X: Telemetry DataFrame.

        Returns:
            np.ndarray: 1D array of float anomaly scores.

        Raises:
            ModelNotFittedError: If model is not fitted.
        """
        if not self.is_fitted_ or self.model_ is None:
            raise ModelNotFittedError("IsolationForestDetector must be fitted before calling score_samples.")

        X_numeric, _ = self._extract_numeric_features(X, enforce_fitted_features=True)
        # Invert native score_samples so higher = more anomalous
        scores = -self.model_.score_samples(X_numeric)
        return scores

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts binary anomaly labels (1 = anomaly, 0 = nominal).

        Args:
            X: Telemetry DataFrame.

        Returns:
            np.ndarray: 1D integer array (0 or 1).
        """
        if not self.is_fitted_ or self.model_ is None:
            raise ModelNotFittedError("IsolationForestDetector must be fitted before calling predict.")

        scores = self.score_samples(X)
        return (scores > self.threshold_).astype(int)

    def explain(self, X: pd.DataFrame, top_k_channels: int = 2) -> pd.DataFrame:
        """Provides observation-level anomaly scores and channel attribution.

        Computes normalized deviations relative to the training distribution to
        identify the top channels driving the anomalous state.

        Args:
            X: Telemetry DataFrame.
            top_k_channels: Number of top contributing channels to identify per row. Defaults to 2.

        Returns:
            pd.DataFrame: Contains anomaly_score, is_anomaly, channel normalized deviations,
                and top_contributing_channels.
        """
        if not self.is_fitted_ or self.model_ is None:
            raise ModelNotFittedError("IsolationForestDetector must be fitted before calling explain.")

        X_numeric, original_index = self._extract_numeric_features(X, enforce_fitted_features=True)
        scores = self.score_samples(X)
        predictions = (scores > self.threshold_).astype(int)

        # Compute per-channel deviations relative to training distribution
        dev_df = pd.DataFrame(index=original_index)
        for col in self.feature_names_:
            mu = self.train_means_[col]
            sigma = self.train_stds_[col]
            dev_df[f"{col}_dev"] = np.abs(X_numeric[col].astype(float) - mu) / sigma

        top_channels_list = []
        for idx in dev_df.index:
            row_devs = dev_df.loc[idx]
            # Sort channels by deviation descending
            sorted_channels = row_devs.sort_values(ascending=False).index.tolist()
            clean_names = [c.replace("_dev", "") for c in sorted_channels[:top_k_channels]]
            top_channels_list.append(", ".join(clean_names))

        explanation_df = dev_df.copy()
        explanation_df["anomaly_score"] = scores
        explanation_df["is_anomaly"] = predictions
        explanation_df["top_contributing_channels"] = top_channels_list
        explanation_df.index = original_index

        return explanation_df

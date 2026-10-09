"""Abstract base detector interface for OrbitGuard AI anomaly detection models.

Defines the contract and conventions for all satellite telemetry anomaly detectors:
- Uniform method signatures: `fit`, `predict`, `score_samples`, `explain`.
- Anomaly score convention: continuous float where higher score = more anomalous.
- Prediction convention: binary integer where 1 = anomaly (alert), 0 = nominal.
- Strict feature/label isolation: rejects ground-truth label columns to prevent leakage.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd


class ModelNotFittedError(ValueError):
    """Raised when an anomaly detector method requiring a fitted model is invoked prematurely."""
    pass


class BaseDetector(ABC):
    """Abstract base class for OrbitGuard AI anomaly detectors.

    Conventions:
    - Score Direction: Higher continuous score strictly indicates higher anomaly severity.
    - Predictions: 1 = Anomaly detected, 0 = Nominal operation.
    - Timestamp Handling: Timestamps are preserved for output alignment but excluded from numeric model inputs.
    - Leakage Prevention: Detectors reject DataFrames containing ground truth label columns ('is_anomaly', 'anomaly_type').
    """

    def __init__(self, timestamp_col: str = "timestamp"):
        self.timestamp_col = timestamp_col
        self.is_fitted_: bool = False
        self.feature_names_: List[str] = []

    def _extract_numeric_features(
        self,
        X: pd.DataFrame,
        enforce_fitted_features: bool = True,
    ) -> Tuple[pd.DataFrame, pd.Index]:
        """Validates input, excludes non-feature columns, and extracts numeric telemetry matrix.

        Args:
            X: Input DataFrame.
            enforce_fitted_features: If True and model is fitted, enforces exact matching feature columns.

        Returns:
            Tuple of (X_numeric, original_index).

        Raises:
            TypeError: If X is not a pandas DataFrame.
            ValueError: If X is empty, contains label columns, or contains non-finite values.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"Input must be a pandas DataFrame, got {type(X).__name__}.")
        if X.empty:
            raise ValueError("Input DataFrame is empty.")

        # Leakage guard: reject ground truth labels
        forbidden_labels = {"is_anomaly", "anomaly_type", "ground_truth", "label"}
        detected_labels = forbidden_labels.intersection(X.columns)
        if detected_labels:
            raise ValueError(
                f"Ground-truth label column(s) {detected_labels} detected in feature matrix! "
                "Labels must be strictly separated from model inputs to prevent data leakage."
            )

        # Exclude timestamp
        cols_to_use = [c for c in X.columns if c != self.timestamp_col]
        if not cols_to_use:
            raise ValueError("No telemetry feature channels found in DataFrame.")

        # If already fitted, enforce the identical feature column list
        if self.is_fitted_ and enforce_fitted_features:
            missing_cols = [c for c in self.feature_names_ if c not in X.columns]
            if missing_cols:
                raise ValueError(f"Input is missing fitted telemetry feature channels: {missing_cols}")
            cols_to_use = list(self.feature_names_)

        X_numeric = X[cols_to_use].copy()

        # Check non-numeric dtypes
        for c in cols_to_use:
            if not pd.api.types.is_numeric_dtype(X_numeric[c]):
                raise ValueError(f"Telemetry channel '{c}' contains non-numeric data.")

        # Check for NaN / Inf
        if X_numeric.isna().any().any():
            raise ValueError("Input telemetry contains NaN/missing values. Validate or preprocess input before inference.")
        if np.isinf(X_numeric.to_numpy()).any():
            raise ValueError("Input telemetry contains infinite values.")

        return X_numeric, X.index

    @abstractmethod
    def fit(self, X: pd.DataFrame) -> "BaseDetector":
        """Fits detector parameters strictly on training observations.

        Args:
            X: Training DataFrame containing telemetry features.

        Returns:
            self: The fitted detector instance.
        """
        pass

    @abstractmethod
    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Computes continuous anomaly scores for each observation.

        Convention: Higher score indicates higher likelihood of anomaly.

        Args:
            X: Telemetry DataFrame.

        Returns:
            np.ndarray: 1D array of float anomaly scores aligned with X's rows.
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts binary anomaly status for each observation.

        Convention: 1 = Anomaly, 0 = Nominal.

        Args:
            X: Telemetry DataFrame.

        Returns:
            np.ndarray: 1D array of integers (0 or 1) aligned with X's rows.
        """
        pass

    @abstractmethod
    def explain(self, X: pd.DataFrame) -> pd.DataFrame:
        """Returns channel-level anomaly attribution details for diagnostic explanations.

        Args:
            X: Telemetry DataFrame.

        Returns:
            pd.DataFrame: Diagnostics and channel contributions aligned with X's rows and index.
        """
        pass

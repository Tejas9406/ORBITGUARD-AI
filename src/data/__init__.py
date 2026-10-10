"""Data handling, validation, loading, and preprocessing package for OrbitGuard AI."""

from src.data.loader import (
    DEFAULT_LABEL_COLS,
    chronological_train_test_split,
    load_telemetry,
    split_features_and_labels,
)
from src.data.preprocessing import (
    NotFittedError,
    TelemetryPreprocessor,
)
from src.data.synthetic import (
    generate_synthetic_telemetry,
)
from src.data.validation import (
    DuplicateRecordError,
    EmptyDataError,
    InvalidTimestampError,
    MissingColumnError,
    MissingValueError,
    NonNumericTelemetryError,
    TelemetryValidationError,
    ValidationReport,
    validate_telemetry,
)

__all__ = [
    # Validation
    "TelemetryValidationError",
    "EmptyDataError",
    "MissingColumnError",
    "InvalidTimestampError",
    "NonNumericTelemetryError",
    "MissingValueError",
    "DuplicateRecordError",
    "ValidationReport",
    "validate_telemetry",
    # Loader
    "DEFAULT_LABEL_COLS",
    "load_telemetry",
    "split_features_and_labels",
    "chronological_train_test_split",
    # Preprocessing
    "NotFittedError",
    "TelemetryPreprocessor",
    # Synthetic
    "generate_synthetic_telemetry",
]

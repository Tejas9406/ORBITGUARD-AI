"""OrbitGuard AI Backend Modules.

Exposes clean, modular components for telemetry ingestion, feature engineering,
hybrid anomaly detection (Statistical, Isolation Forest, Pretrained LSTM),
comparative evaluation, and spacecraft fleet health assessment.
"""

from .data import DatasetAudit, TelemetryDataset
from .events import group_events
from .features import build_features
from .isolation_forest import TelemetryIsolationForest, run_isolation_forest_detection
from .lstm_inference import (
    compute_prediction_errors,
    detect_lstm_anomalies,
    load_lstm_weights,
    run_lstm_forward,
    shape_lstm_input,
)
from .calibration import (
    CalibratedThreshold,
    calibrate_all_thresholds,
    calibrate_lstm_threshold,
    calibrate_statistical_threshold,
)
from .evaluation import EvaluationMetrics, compare_all_detectors, evaluate_event_detection
from .health import (
    ChannelHealthSummary,
    SpacecraftFleetHealth,
    assess_channel_health,
    compute_spacecraft_health_overview,
)
from .history import EvaluationHistory, EvaluationRun
from .ingestion import (
    SourceType,
    TelemetryInput,
    ValidationReport,
    ValidationStatus,
    ingest_csv,
    ingest_nasa_channel,
    validate_and_prepare,
)
from .pipeline import process_dataset

__all__ = [
    "DatasetAudit",
    "TelemetryDataset",
    "process_dataset",
    "build_features",
    "group_events",
    "TelemetryIsolationForest",
    "run_isolation_forest_detection",
    "load_lstm_weights",
    "shape_lstm_input",
    "run_lstm_forward",
    "compute_prediction_errors",
    "detect_lstm_anomalies",
    "EvaluationMetrics",
    "compare_all_detectors",
    "evaluate_event_detection",
    "ChannelHealthSummary",
    "SpacecraftFleetHealth",
    "assess_channel_health",
    "compute_spacecraft_health_overview",
    "ValidationStatus",
    "SourceType",
    "ValidationReport",
    "TelemetryInput",
    "validate_and_prepare",
    "ingest_csv",
    "ingest_nasa_channel",
    "CalibratedThreshold",
    "calibrate_statistical_threshold",
    "calibrate_lstm_threshold",
    "calibrate_all_thresholds",
    "EvaluationRun",
    "EvaluationHistory",
]


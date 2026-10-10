"""Reusable detector protocol for OrbitGuard AI.

Detectors declare the schemas they accept. Orchestration selects compatible
detectors; it never pads or fabricates features to force a model to run.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .contracts import TelemetryContract
from .ingestion import TelemetryInput


@dataclass
class DetectorCapability:
    detector_id: str
    display_name: str
    detector_type: str
    requires_training_partition: bool
    supports_univariate: bool
    supports_multivariate: bool
    requires_pretrained_artifact: bool
    accepted_sources: List[str]  # empty means any, subject to artifact contracts
    limitations: str


@dataclass
class CompatibilityReport:
    detector_id: str
    compatible: bool
    outcome: str
    reason: str
    would_status: str  # EXECUTED if run, else SKIPPED


class Detector(ABC):
    capability: DetectorCapability

    def check_compatibility(
        self,
        telemetry: TelemetryInput,
        contract: Optional[TelemetryContract] = None,
    ) -> CompatibilityReport:
        cap = self.capability
        if telemetry.feature_dim <= 0:
            return CompatibilityReport(cap.detector_id, False, "INVALID", "No features present.", "SKIPPED")
        if telemetry.feature_dim == 1 and not cap.supports_univariate:
            return CompatibilityReport(cap.detector_id, False, "INCOMPATIBLE_FEATURES", "Detector does not support univariate channels.", "SKIPPED")
        if telemetry.feature_dim > 1 and not cap.supports_multivariate:
            return CompatibilityReport(cap.detector_id, False, "INCOMPATIBLE_FEATURES", "Detector does not support multivariate tensors.", "SKIPPED")
        if cap.requires_training_partition and telemetry.train_data is None:
            return CompatibilityReport(
                cap.detector_id,
                False,
                "MISSING_TRAIN",
                "No permitted training/reference partition. This detector will not fit on the evaluation window.",
                "SKIPPED",
            )
        if cap.accepted_sources and telemetry.source_dataset not in cap.accepted_sources and telemetry.source_dataset != "UNKNOWN":
            # Statistical baseline accepts all sources even if list is empty; pretrained models restrict.
            if cap.requires_pretrained_artifact:
                return CompatibilityReport(
                    cap.detector_id,
                    False,
                    "UNSUPPORTED_SOURCE",
                    f"Detector trained for {cap.accepted_sources}, not '{telemetry.source_dataset}'.",
                    "SKIPPED",
                )
        return self._check_extra(telemetry, contract)

    def _check_extra(self, telemetry: TelemetryInput, contract: Optional[TelemetryContract]) -> CompatibilityReport:
        return CompatibilityReport(self.capability.detector_id, True, "COMPATIBLE", "Compatible.", "EXECUTED")

    @abstractmethod
    def identify(self) -> Dict[str, Any]:
        ...


class StatisticalDetector(Detector):
    capability = DetectorCapability(
        detector_id="statistical_baseline",
        display_name="Statistical Baseline (Median/MAD)",
        detector_type="Statistical Baseline",
        requires_training_partition=False,
        supports_univariate=True,
        supports_multivariate=True,
        requires_pretrained_artifact=False,
        accepted_sources=[],
        limitations="Uses a causal rolling robust z-score. Calibrates on training data when available; otherwise a documented default threshold.",
    )

    def identify(self) -> Dict[str, Any]:
        return {"model_id": "statistical_baseline", "version": "1.0.0", "architecture": "causal robust rolling z-score"}


class IsolationForestDetector(Detector):
    capability = DetectorCapability(
        detector_id="isolation_forest",
        display_name="Isolation Forest",
        detector_type="Machine Learning (Isolation Forest)",
        requires_training_partition=True,
        supports_univariate=True,
        supports_multivariate=True,
        requires_pretrained_artifact=False,
        accepted_sources=[],
        limitations="Fits only on a permitted training partition. Will skip if the only available data is the evaluation window.",
    )

    def identify(self) -> Dict[str, Any]:
        return {"model_id": "isolation_forest", "version": "1.0.0", "architecture": "pure-numpy isolation forest"}


class NASALstmDetector(Detector):
    capability = DetectorCapability(
        detector_id="nasa_telemanom_lstm",
        display_name="Pretrained Telemanom LSTM",
        detector_type="Deep Learning (Fresh Inference)",
        requires_training_partition=False,
        supports_univariate=False,
        supports_multivariate=True,
        requires_pretrained_artifact=True,
        accepted_sources=["NASA_SMAP_MSL"],
        limitations="Requires NASA SMAP (25-dim) or MSL (55-dim) tensors and matching channel weights. Not used for ESA or CSV uploads.",
    )

    def _check_extra(self, telemetry: TelemetryInput, contract: Optional[TelemetryContract]) -> CompatibilityReport:
        if telemetry.source_dataset != "NASA_SMAP_MSL":
            return CompatibilityReport(
                self.capability.detector_id, False, "UNSUPPORTED_SOURCE",
                "NASA LSTM is only valid for NASA_SMAP_MSL contracts.", "SKIPPED",
            )
        if not telemetry.lstm_compatible:
            return CompatibilityReport(
                self.capability.detector_id, False, "INCOMPATIBLE_FEATURES",
                f"NASA LSTM expects 25 or 55 features; received {telemetry.feature_dim}.", "SKIPPED",
            )
        return CompatibilityReport(self.capability.detector_id, True, "COMPATIBLE", "NASA LSTM input layout matches.", "EXECUTED")

    def identify(self) -> Dict[str, Any]:
        return {"model_id": "nasa_telemanom_lstm", "version": "telemanom_v2", "architecture": "2-layer LSTM"}


class ESALstmDetector(Detector):
    capability = DetectorCapability(
        detector_id="esa_sequence_lstm",
        display_name="ESA-Trained Sequence LSTM",
        detector_type="Deep Learning (ESA OPS-SAT LSTM)",
        requires_training_partition=False,
        supports_univariate=True,
        supports_multivariate=False,
        requires_pretrained_artifact=True,
        accepted_sources=["ESA_OPS_SAT_AD"],
        limitations="Requires a channel-specific ESA artifact. Other satellites are not inferred from matching 1-D shapes.",
    )

    def _check_extra(self, telemetry: TelemetryInput, contract: Optional[TelemetryContract]) -> CompatibilityReport:
        if telemetry.source_dataset != "ESA_OPS_SAT_AD":
            return CompatibilityReport(
                self.capability.detector_id, False, "UNSUPPORTED_SOURCE",
                "ESA LSTM artifacts are not applied to non-ESA sources.", "SKIPPED",
            )
        return CompatibilityReport(self.capability.detector_id, True, "COMPATIBLE", "ESA source contract accepted; artifact still required per channel.", "EXECUTED")

    def identify(self) -> Dict[str, Any]:
        return {"model_id": "esa_sequence_lstm", "version": "1.0.0", "architecture": "NumPy autoregressive RNN"}


def default_detectors() -> List[Detector]:
    return [
        StatisticalDetector(),
        IsolationForestDetector(),
        NASALstmDetector(),
        ESALstmDetector(),
    ]


def compatible_detector_reports(
    telemetry: TelemetryInput,
    contract: Optional[TelemetryContract] = None,
) -> List[CompatibilityReport]:
    return [d.check_compatibility(telemetry, contract) for d in default_detectors()]

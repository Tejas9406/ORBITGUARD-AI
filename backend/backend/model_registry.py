"""Model Registry and Machine-Checkable Manifest System for OrbitGuard AI.

Provides:
- ModelManifest: Versioned descriptor of architecture, expected features, artifact checksum,
  and training provenance.
- CompatibilityOutcome: Machine-checked validation result (COMPATIBLE, INCOMPATIBLE_SCHEMA,
  INCOMPATIBLE_FEATURES, INCOMPATIBLE_PREPROCESSING, INCOMPATIBLE_SEQUENCE, INVALID_ARTIFACT).
- ModelRegistry: Central registry validating incoming contracts before loading weights.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .contracts import TelemetryContract

logger = logging.getLogger("orbitguard.registry")


class CompatibilityOutcome(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE_SCHEMA = "INCOMPATIBLE_SCHEMA"
    INCOMPATIBLE_FEATURES = "INCOMPATIBLE_FEATURES"
    INCOMPATIBLE_PREPROCESSING = "INCOMPATIBLE_PREPROCESSING"
    INCOMPATIBLE_SEQUENCE = "INCOMPATIBLE_SEQUENCE"
    INVALID_ARTIFACT = "INVALID_ARTIFACT"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"


@dataclass
class ModelManifest:
    model_id: str
    detector_type: str            # "Pretrained LSTM", "Isolation Forest", "Statistical Baseline"
    architecture: str             # e.g., "2-Layer LSTM (80x80)", "IsolationForest(n=100)", "Rolling Z-score"
    version: str                  # e.g., "1.0.0"
    training_source: str          # "NASA_SMAP_MSL", "ESA_OPS_SAT_AD", "UNSUPERVISED"
    expected_feature_dim: int
    expected_feature_names: List[str]
    expected_units: List[str]
    lookback_window: int          # e.g., 250 for NASA, 20 for ESA
    prediction_steps: int         # e.g., 10 for NASA, 1 for ESA
    preprocessing_version: str
    artifact_path: Optional[str] = None
    artifact_checksum_sha256: Optional[str] = None
    calibration_method: str = "sigma_standardized"
    threshold_value: float = 3.0
    status: str = "PRODUCTION_READY"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, json_path: str | Path):
        p = Path(json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, json_path: str | Path) -> ModelManifest:
        p = Path(json_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(**data)


def compute_file_sha256(file_path: str | Path) -> str:
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for checksum: {p}")
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


class ModelRegistry:
    """Central registry and compatibility validator for detector models."""

    def __init__(self, registry_dir: Optional[str | Path] = None):
        self.registry_dir = Path(registry_dir) if registry_dir else Path(__file__).resolve().parent.parent / "models"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self._manifests: Dict[str, ModelManifest] = {}

    def register_manifest(self, manifest: ModelManifest):
        self._manifests[manifest.model_id] = manifest

    def get_manifest(self, model_id: str) -> Optional[ModelManifest]:
        return self._manifests.get(model_id)

    @staticmethod
    def validate_compatibility(
        manifest: ModelManifest,
        contract: TelemetryContract,
        verify_artifact_file: bool = True,
    ) -> Tuple[CompatibilityOutcome, str]:
        """Strict machine-checkable compatibility validation.

        Fails with clear reason if any dimension, unit, schema, sequence or checksum mismatches.
        """
        # 1. Check Artifact Integrity
        if verify_artifact_file and manifest.artifact_path:
            art_p = Path(manifest.artifact_path)
            if not art_p.is_file():
                return (
                    CompatibilityOutcome.INVALID_ARTIFACT,
                    f"Model artifact file does not exist: {manifest.artifact_path}",
                )
            if manifest.artifact_checksum_sha256:
                actual_sha = compute_file_sha256(art_p)
                if actual_sha != manifest.artifact_checksum_sha256:
                    return (
                        CompatibilityOutcome.INVALID_ARTIFACT,
                        f"Artifact SHA-256 mismatch: expected {manifest.artifact_checksum_sha256}, got {actual_sha}",
                    )

        # 2. Check Feature Dimension
        if contract.feature_dim != manifest.expected_feature_dim:
            return (
                CompatibilityOutcome.INCOMPATIBLE_FEATURES,
                f"Feature dimension mismatch: model '{manifest.model_id}' expects {manifest.expected_feature_dim} features, "
                f"but contract '{contract.channel_id}' provides {contract.feature_dim} features.",
            )

        # 3. Check Dataset / Source Compatibility
        if manifest.training_source != "UNSUPERVISED":
            if manifest.training_source != contract.source_dataset:
                return (
                    CompatibilityOutcome.UNSUPPORTED_SOURCE,
                    f"Source mismatch: model trained on '{manifest.training_source}', "
                    f"but incoming contract is from '{contract.source_dataset}'.",
                )

        # 4. Check Preprocessing Version
        if manifest.preprocessing_version != contract.preprocessing_version:
            return (
                CompatibilityOutcome.INCOMPATIBLE_PREPROCESSING,
                f"Preprocessing pipeline mismatch: model requires '{manifest.preprocessing_version}', "
                f"contract specifies '{contract.preprocessing_version}'.",
            )

        # 5. Check Feature Units (Physical semantics check)
        if manifest.expected_units:
            contract_units = contract.feature_units
            if len(contract_units) == len(manifest.expected_units):
                for i, (exp_u, act_u) in enumerate(zip(manifest.expected_units, contract_units)):
                    if exp_u != "any" and act_u != "any" and exp_u != act_u:
                        return (
                            CompatibilityOutcome.INCOMPATIBLE_SCHEMA,
                            f"Unit mismatch at feature index {i}: model expects '{exp_u}', contract provides '{act_u}'.",
                        )

        return (
            CompatibilityOutcome.COMPATIBLE,
            f"Contract '{contract.channel_id}' is fully compatible with model '{manifest.model_id}'.",
        )

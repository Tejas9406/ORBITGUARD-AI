# ORBITGUARD-AI: Model Compatibility Root-Cause Investigation Report

**Investigation Date:** 2026-10-10  
**Authors:** Senior ML Engineer & Satellite Telemetry Systems Specialist  
**Workspace:** `C:\Users\Admin\Downloads\Fusion\telemanom`

---

## 1. Executive Summary

This investigation analyzes the architectural root cause behind model compatibility failures when attempting to evaluate pretrained NASA Telemanom LSTM weights on European Space Agency (ESA) OPS-SAT-1 telemetry.

The failure was not merely an implementation bug or runtime error; it was an architectural mismatch caused by the absence of a machine-checkable Telemetry Contract and Model Registry. Without contracts, feature counts, channel semantics, and preprocessing pipelines were implicitly assumed rather than explicitly verified.

---

## 2. Technical Root Cause Analysis: NASA Telemanom LSTM vs. ESA OPS-SAT-1

### 2.1 Model Architecture & Tensor Expectations of NASA Weights
- **Model Checkpoints:** `data/2018-05-19_15.00.10/models/<channel>.h5`
- **Tensor Input Shape:** `(Batch, Lookback=250, Features)`
  - For SMAP channels (e.g., `P-1`): `Features = 25` (Column 0: primary telemetry signal; Columns 1–24: one-hot command vectors and binary flags).
  - For MSL channels (e.g., `M-1`): `Features = 55`.
- **First-Layer Kernel Weight Shape:**
  - `W1` kernel tensor is shaped `(25, 320)` where $320 = 4 \times 80$ LSTM hidden units.
  - Matrix multiplication $X \cdot W_1$ strictly requires $X$ to have feature dimension matching $W_1.shape[0]$.
- **Prediction Target:** 10-step lookahead vector `y` predicting future values of Column 0.

### 2.2 ESA OPS-SAT-1 Telemetry Characteristics
- **Dataset:** `segments.csv` (Zenodo 15108715, ESA OPS-SAT-AD).
- **Channels:** 9 distinct ADCS sensors (`CADC0872` Gyro X, `CADC0873` Gyro Y, `CADC0874` Gyro Z, `CADC0892` Sun Sensor Elevation, etc.).
- **Dimensionality:** Each channel is downlinked as an independent scalar time series (Feature Dimension = 1).
- **Physical Semantics & Units:** Gyro angular velocity in $\text{rad/s}$ (range $\pm 10^{-4}$), Sun sensor elevation in $\text{rad}$ (range $[0, 1.57]$).
- **Sampling Cadence:** 1 Hz during ground station passes with multi-day inter-pass gaps.

### 2.3 Why NASA Weights Cannot Consume ESA Telemetry
1. **Mathematical Dimensionality Incompatibility:**
   - Passing ESA univariate data ($D=1$) into the NASA kernel ($D=25$) fails matrix multiplication ($\text{Inner dimensions } 1 \ne 25$).
2. **Semantic Meaning Mismatch:**
   - The NASA 24 auxiliary columns represent specific SMAP mission command commands. Forcing ESA telemetry into these columns would violate physics and deceive operators.
3. **Sequence & Scale Disparity:**
   - NASA SMAP signals are min-max scaled to $[-1, +1]$. ESA rate gyro readings are naturally centered near $0.0 \pm 10^{-5}$ rad/s.
   - NASA lookback of 250 steps with continuous telemetry assumption fails across ESA inter-pass gaps.

---

## 3. Vulnerability Audit: Where Incompatibilities Could Silently Fail

1. **Silent Detector Skipping in Coordinator (`backend/coordinator.py`):**
   - When LSTM dimension check failed, the coordinator previously created an empty result without propagating a machine-readable failure reason, leading downstream consensus to assume 0 detected events rather than an unexecuted detector.
2. **Consensus Aggregation Without Execution Filtering:**
   - Consensus calculation previously clustered events without checking if detectors were `SKIPPED` or `FAILED`.
3. **Health Assessment Invariant Drift (`backend/health.py`):**
   - Invariant $\text{detected} = \text{TP} + \text{FP}$ was violated when multiple events overlapped the same ground-truth interval, causing TP double-counting or discrepancies.
4. **Ad-Hoc Threshold Calibration Leakage Risk:**
   - Passing `ground_truth_ranges` into functions that perform threshold calibration creates the risk of test-label leakage unless strict partition barriers exist.

---

## 4. Architectural Remediation Plan

To permanently prevent recurring compatibility issues across any satellite mission:

1. **Phase 2: Strict, Versioned Telemetry Contract (`backend/contracts.py`):**
   - Defines `TelemetryContract` with source, mission, ordered feature names, units, sampling cadence, missing-data rules, and split boundaries.
2. **Phase 3: Model Registry & Machine-Checkable Manifests (`backend/model_registry.py`):**
   - Versioned model manifests (`ModelManifest`) storing architecture, expected features, artifact checksums, and explicit compatibility states (`COMPATIBLE`, `INCOMPATIBLE_FEATURES`, `INCOMPATIBLE_SEQUENCE`, etc.).
3. **Phase 4: Dedicated, Trainable ESA LSTM Architecture (`backend/esa_lstm.py`):**
   - Pure-NumPy lightweight trainable LSTM tailored for ESA univariate time series ($D=1$, lookback $L=20$, $H=16$), fitted strictly on the official training split (`train == 1`), calibrated on validation split, and validated on held-out test split (`train == 0`).
4. **Phase 5: Fail-Safe Detector Execution Records:**
   - Every detector emits a `DetectorExecutionRecord` with explicit lifecycle statuses (`EXECUTED`, `SKIPPED`, `FAILED`).
5. **Phase 6: Exhaustive Regression Test Suite (`tests/test_compatibility_regressions.py`):**
   - 22 targeted test scenarios verifying contracts, manifest checks, consensus safeguards, and gap breaking.
6. **Phase 8: Automated Release Gate Script (`scripts/validate_compatibility.py`):**
   - Validates all manifests, contracts, and regression tests with non-zero exit code on failure.

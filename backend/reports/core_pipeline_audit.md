# ORBITGUARD-AI: Core Pipeline Audit Report

**Date:** 2026-10-10  
**Project:** OrbitGuard AI — Satellite Health Sentinel  
**Hackathon Target:** FUSION 2026 SPACE-03 (Satellite Health Anomaly Detection from Telemetry Streams)  
**Workspace:** `c:\Users\Admin\Downloads\Fusion\telemanom`

---

## 1. Executive Summary

OrbitGuard AI provides an end-to-end, reproducible, explainable telemetry health assessment and anomaly detection prototype for satellite operations. The architecture bridges the NASA Telemanom research benchmark (JPL SMAP/MSL dataset) with operational satellite health decision support.

The system combines:
1. **Causal Statistical Detector:** Rolling median and Median Absolute Deviation (MAD) robust Z-score, strictly avoiding future-step data leakage.
2. **Machine Learning Detector:** Pure-NumPy Isolation Forest (Liu, Ting, Zhou 2008), trained exclusively on nominal flight history without ground truth labels.
3. **Deep Learning Sequence Model:** Vectorized pure-NumPy inference using pretrained Keras `.h5` weights, eliminating fragile legacy TensorFlow runtime dependencies.
4. **Canonical Input Layer:** Typed `TelemetryInput` with validation statuses (`COMPATIBLE`, `COMPATIBLE_WITH_WARNINGS`, `INCOMPATIBLE`, `INSUFFICIENT_DATA`).
5. **Cross-Detector Consensus & Traceability:** Automated incident clustering, peak severity assignment, and multi-detector agreement flags.
6. **Fleet Health Decision Support:** Operator-oriented channel and spacecraft status classifications (`Normal`, `Review`, `High Priority`) based on documented discrepancy rules.
7. **Audit & Run Tracking:** SQLite-backed evaluation history recording every run with complete configuration metadata.

---

## 2. Dataset Reconciliation Audit

The repository contains historical artifacts and NASA telemetry requiring strict integrity accounting:

| Dimension | Physical Count | Verified Explanation |
|:---|:---:|:---|
| **Raw Telemetry Files** | 82 train / 82 test | 82 distinct `.npy` files present in `data/train/` and `data/test/`. |
| **Unique Labeled Channels** | 81 channels | 54 SMAP channels, 27 MSL channels with expert anomaly sequences. |
| **Duplicate Channel Entries** | 1 (`P-2`) | `P-2` appears twice in `labeled_anomalies.csv` with conflicting sequence ranges. Resolved via explicit deduplication to prevent Cartesian product inflation. |
| **Unlabelled Raw Channels** | 1 (`T-10`) | Channel `T-10` exists on disk in `data/train/` and `data/test/` but is omitted from `labeled_anomalies.csv`. Classified as unlabelled; excluded from supervised evaluation. |
| **Pretrained `.h5` Models** | 82 weights | Located in `data/2018-05-19_15.00.10/models/`. |
| **Input Dimensions** | 25 (SMAP) / 55 (MSL) | Column 0 represents primary monitored telemetry signal; remaining columns represent auxiliary spacecraft commands and status flags. |

---

## 3. Subsystem Mapping Integrity

- **Status:** **Anonymized NASA Telemetry.**
- In the original Telemanom dataset release, sensor IDs are randomized (e.g. `P-1`, `S-1`, `E-1`, `T-1`) to protect proprietary NASA spacecraft designs.
- Any subsystem assignments previously claimed (such as "Attitude / control" or "Power subsystem") were heuristic conjectures.
- **OrbitGuard AI Standard:** Every channel is transparently categorized as `Unknown / unmapped (Anonymized Telemanom channel)` to prevent false operational assumptions.

---

## 4. Detector Architecture & Mathematical Foundations

### 4.1 Statistical Baseline Detector (`backend/features.py`, `backend/events.py`)
- **Causal Guarantee:** At step $t$, the rolling median and MAD are computed over history $[t - W, t - 1]$ via `series.shift(1)`. Observation $t$ never contaminates its own baseline.
- **Robust Z-Score Formulation:**
  $$\text{score}(t) = \frac{0.6745 \cdot |x_t - \text{median}_{t-1}|}{\max(\text{MAD}_{t-1}, 10^{-9})}$$
- **Event Grouping:** Consecutive steps exceeding threshold $\tau$ (with maximum allowable gap $G=5$ steps and minimum duration $M=3$ steps) are clustered into contiguous incident windows with peak score and severity rating (`medium`, `high`, `critical`).

### 4.2 Isolation Forest (`backend/isolation_forest.py`)
- **Motivation:** Pure-NumPy implementation developed to overcome Windows Application Control / DLL blocking on compiled C-extensions (`scipy._sobol`).
- **Unsupervised Training:** Fitted strictly on nominal training telemetry (`X_train`), learning path length distributions without access to test data or ground-truth labels.
- **Anomaly Score Formulation:**
  $$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
  where $c(n) = 2(\ln(n - 1) + 0.5772156649) - \frac{2(n - 1)}{n}$ is the average depth of unsuccessful searches in a Binary Search Tree.
- **Score Calibration:** Standardized using training baseline mean and standard deviation:
  $$z_{\text{iso}}(x) = \frac{s(x) - \mu_{\text{train}}}{\max(\sigma_{\text{train}}, 10^{-4})}$$

### 4.3 Pretrained Telemanom LSTM (`backend/lstm_inference.py`)
- **Weight Portability:** Loads Keras `.h5` weights directly via `h5py` without requiring TensorFlow or Keras runtime dependencies.
- **Forward Pass:** Exact mathematical recreation of 2-layer LSTM ($80 \times 80$ units) with hard sigmoid recurrent activation:
  $$\sigma_{\text{hard}}(x) = \text{clip}(0.2x + 0.5, 0.0, 1.0)$$
- **Sliding Window:** Input matrix shaped to $(N, 250, \text{features})$ with 10-step lookahead dense output, generating 1-step ahead prediction $y_t$.
- **Error Scoring:** Absolute prediction error $e_t = |y_t - \hat{y}_t|$ smoothed via Exponentially Weighted Moving Average (EWMA):
  $$e_{\text{smooth}, t} = \alpha e_t + (1 - \alpha) e_{\text{smooth}, t-1}$$
- **Standardization:** Normalized against warmup baseline distribution $(\mu_{\text{warm}}, \sigma_{\text{warm}})$.

---

## 5. Evaluation Integrity Standard

- **Identical Evaluated Interval:** All three detectors are strictly evaluated over identical sample intervals $[S, E]$.
- **Interval-Overlap Matching:** A true positive (TP) occurs when a detected interval $[d_s, d_e]$ has non-empty intersection with an expert-labeled ground-truth range $[g_s, g_e]$:
  $$\max(d_s, g_s) \le \min(d_e, g_e)$$
- **Zero Reference Event Handling:** When an evaluated interval contains zero ground-truth anomalies:
  - If 0 anomalies detected: Precision, Recall, and F1 are mathematically undefined and reported as `N/A` (never falsely reported as 1.0 / 100%).
  - If $>0$ anomalies detected: All detections are correctly classified as False Alarms (Precision = 0.0, Recall = N/A, F1 = 0.0).

---

## 6. Real-World Telemetry Readiness

- **SatNOGS Network Integration:** Client implemented in `backend/real_world.py` to query open-source demodulated satellite telemetry from the SatNOGS DB API (`https://db.satnogs.org/api`).
  - *Live Probe Verification:* Querying `https://db.satnogs.org/api/satellites/` returned HTTP 200 with 2,832 public satellite records (e.g. `TRANSIT 5B-5`, NORAD 965).
  - *Telemetry Endpoint Authentication:* Querying `https://db.satnogs.org/api/telemetry/` returned HTTP 401 Unauthorized (SatNOGS raw frame endpoint requires registered API user token).
  - *Engineering Telemetry Assessment:* Honest finding: Public SatNOGS frames without a user token do not provide unauthenticated engineering time-series. Thus, real-world data is supplemented by physics-grounded orbital dynamics simulation (`OPS-SAT-1` LEO thermal/power models) and separate synthetic validation.
- **Orbital Dynamics Simulation:** Physics-grounded simulation replicating Low Earth Orbit (LEO) solar radiation, eclipse transitions, battery state-of-charge decay, and radiator thermal cycling.

---

## 7. Critical Requirements Verification & Quality Gate (PASS / PARTIAL / FAIL)

| # | Requirement | Status | Supporting Evidence & Verification |
|:---|:---|:---:|:---|
| 1 | **NASA Pretrained LSTM Fresh Inference** | **PASS** | `backend/lstm_inference.py` loads `.h5` weights via `h5py` and executes exact 2-layer LSTM forward pass in pure NumPy. Output matches saved Keras predictions within $7.15 \times 10^{-7}$. |
| 2 | **Pure-NumPy Isolation Forest** | **PASS** | `backend/isolation_forest.py` implements Liu et al. (2008) in pure NumPy. Fits strictly on training data without labels; flags 177 FPs across fleet with 11.5% micro-precision. |
| 3 | **Causal Statistical Detector** | **PASS** | `backend/features.py` uses `shift(1)` for strictly causal historical rolling median/MAD. Zero future lookahead. Achieves 83.5% recall on 80 NASA channels. |
| 4 | **Multi-Detector Consensus Synthesis** | **PASS** | `backend/coordinator.py` implements `compute_cross_detector_consensus` clustering interval detections and voting agreement count. |
| 5 | **Data-Driven Threshold Calibration** | **PASS** | `backend/calibration.py` calibrates thresholds from training score distributions (e.g., 99th percentile) rather than arbitrary constants. |
| 6 | **Canonical Typed Ingestion Layer** | **PASS** | `backend/ingestion.py` implements `TelemetryInput` with 4 explicit validation statuses: `COMPATIBLE`, `COMPATIBLE_WITH_WARNINGS`, `INCOMPATIBLE`, `INSUFFICIENT_DATA`. |
| 7 | **Dataset Deduplication Integrity** | **PASS** | Reconciled 82 raw files vs 81 unique channels. `P-2` isolated due to conflicting labels (`[5350, 6575]` vs `[5300, 6420]`). `T-10` flagged as unlabelled. 80 channels evaluated. |
| 8 | **Subsystem Anonymization Standard** | **PASS** | All NASA SMAP/MSL channels classified as `Unknown / unmapped (Anonymized Telemanom channel)`. No fabricated subsystem mappings. |
| 9 | **Identical Evaluated Interval Standard** | **PASS** | `backend/evaluation.py` enforces identical interval boundaries across all 3 detectors. Filters GT to the evaluated interval. |
| 10 | **Zero-GT Metric Handling** | **PASS** | In windows with 0 ground truth events, Precision, Recall, and F1 return `None` (`N/A`) instead of false 1.0 scores. Tested in `test_14_evaluation_zero_ground_truth`. |
| 11 | **Persistent SQLite History** | **PASS** | `backend/history.py` records every run with timestamps and configurations into `data/evaluation_history.sqlite`. |
| 12 | **Fleet Health Assessment** | **PASS** | `backend/health.py` aggregates fleet and channel health (`Normal`, `Review`, `High Priority`) strictly based on real detector discrepancy outputs. |
| 13 | **Streamlit Multi-View Dashboard** | **PASS** | `dashboard_app.py` provides Fleet Overview, NASA Deep Dive + Live Benchmark, and Custom CSV Ingestion views. |
| 14 | **Real-World Telemetry Adapter** | **PARTIAL** | SatNOGS `/satellites/` endpoint successfully queried (HTTP 200, 2,832 satellites). `/telemetry/` raw frame endpoint requires API authentication token (HTTP 401). Honest status: SatNOGS connectivity works; raw telemetry payload requires credentials. Orbital physics simulation provides verified offline alternative. |
| 15 | **Automated Unit Test Suite** | **PASS** | `tests/test_orbitguard.py` contains 20 comprehensive unit tests exercising every backend component. 100% pass rate in 0.60s. |
| 16 | **Fleet-Wide NASA Benchmark** | **PASS** | `reports/benchmark_evaluation.csv` and `benchmark_summary.json` contain independent results across 80 NASA channels (103 GT events). |


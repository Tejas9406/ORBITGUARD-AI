# OrbitGuard AI — Streamlit Telemetry Sentinel Dashboard

## Overview

`dashboard_app.py` is the interactive Streamlit telemetry investigation and health monitoring platform for **ORBITGUARD-AI** (FUSION 2026 SPACE-03: Satellite Health Anomaly Detection from Telemetry Streams).

It runs on modern Python (Python 3.10+) with Streamlit and Plotly, independent of the legacy 2019 Telemanom dependencies.

---

## 3 Core Functional Views

### 1. 🛰️ Mission Fleet Health Overview
- **Fleet-Wide Aggregation:** Decision-support monitoring across active satellite missions:
  - **NASA SMAP** (54 unique channels)
  - **NASA MSL** (27 unique channels)
  - **ESA OPS-SAT-1** (Real UHF engineering telemetry stream)
- **Reconciliation Audit:** Reconciles 82 raw NASA `.npy` files with 81 unique benchmark channels (including unlabelled `T-10` audit and deduplicated `P-2`).
- **Telemetry Health Status:** Transparent, rule-based status flags (`Normal`, `Review`, `High Priority`) with documented operator justifications.
- **Mission Health Metrics:** Channels monitored, channels with alerts, total flagged events, reference ground-truth events, and false alarm / missed event ratios.
- **Detailed Subsystem Table:** Breakdown of every monitored channel with detected events, reference labels, and engineering explanations.

### 2. 🔍 Mission Channel Deep Dive & Multi-Detector Benchmark
- **Channel Selection:** Switch across ESA OPS-SAT-1 ADCS channels (e.g. `CADC0872`, `CADC0892`) and NASA SMAP/MSL channels (e.g. `P-1`, `A-1`).
- **Interactive Timeline Signal Chart:**
  - Observed telemetry signal
  - Expert reference anomaly intervals (pink/red)
  - Cross-detector consensus alerts (green)
- **Multi-Detector Anomaly Score Chart:**
  - Real-time score traces for all executed detectors:
    1. **Statistical Robust Z-Score** (orange)
    2. **Isolation Forest Unsupervised ML** (teal)
    3. **Pretrained Sequence LSTM** (purple)
  - Configurable alert threshold lines.
- **Pipeline Execution Status:** Transparent card status (`EXECUTED`, `SKIPPED`, `FAILED`) reporting exact operational reason (e.g., contract dimension checks).
- **Comparative Evaluation Benchmark:** Side-by-side comparison of Precision, Recall, F1 Score, TP, FP, FN, and execution time over identical evaluation intervals.
- **Consensus Alert Evidence Table:** Start step, end step, duration, agreeing detector models, peak score, and timestamps where available.

### 3. 📁 Custom Telemetry CSV Ingestion & Hybrid Detection
- **Arbitrary External Telemetry:** Allows flight controllers and scientists to upload any telemetry CSV or load preloaded demo telemetry (Solar Panel Voltage, Battery Temp, Gyro Z).
- **Causal Hybrid Detection:** Automatically deploys rolling Robust Z-Score and Isolation Forest detectors on numeric streams without future leakage.
- **Interactive Visualizations:** Time-series signal chart with severity-colored anomaly bands (`Critical`, `High`, `Moderate`), score trajectories, and threshold controls.
- **Executive Satellite Health Review Report:**
  - Operational Status: `Normal` (green), `Review` (orange), or `High Priority` (red).
  - Diagnostic Justification Narrative based on flagged event count, severity, and rate of deviation.
  - Telemetry Stream Stability Index (`% nominal observations`).
  - Subsystem Diagnostic Findings (excursion magnitude, persistent drift, or transient jitter).
  - Actionable Flight Controller Remediation Recommendations.
- **Report Export:**
  - 📥 **Download Health Review Report (JSON):** Full machine-readable audit report.
  - 📄 **Download Executive Summary (Markdown):** Formatted summary for mission flight directors.

---

## How to Run Locally

```powershell
# In the telemanom folder:
cd telemanom
python -m pip install -r requirements-dashboard.txt
streamlit run dashboard_app.py
```

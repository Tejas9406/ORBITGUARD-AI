# Real-World Satellite Telemetry Data Source Report

**Author:** OrbitGuard AI Engineering Team  
**Workspace:** `c:\Users\Admin\Downloads\Fusion\telemanom`  
**Date:** 2026-10-10

---

## 1. Executive Summary

This report documents our empirical investigation of genuine public satellite telemetry sources for OrbitGuard AI:
1. **SatNOGS Network & DB API:** The premier global open-source ground station network.
2. **ESA Open Telemetry Datasets (OPS-SAT, Solar Orbiter, Mars Express).**
3. **NASA Telemanom Benchmark (JPL SMAP & MSL).**

We present the findings from live connectivity probes, data schema analysis, operational constraints, and the design of the OrbitGuard AI real-world ingestion adapter (`backend/real_world.py`).

---

## 2. Public Satellite Telemetry Source Analysis

### 2.1 SatNOGS Network (Libre Space Foundation)
- **Base Endpoint:** `https://db.satnogs.org/api`
- **Description:** A global network of satellite ground stations receiving transmissions from low Earth orbit (LEO) satellites.
- **Available Data:** Demodulated binary frames, transmitter frequencies, RF signal metrics, decoded beacon telemetries.
- **Relevant Satellites:**
  - `OPS-SAT` (NORAD 44878) — ESA technology testbed nanosatellite.
  - `NOAA-15 / 18 / 19` (NORAD 25338, 28654, 33591) — Polar operational environmental satellites.
  - `ISS / ZARYA` (NORAD 25544) — International Space Station APRS/telemetry beacons.
- **Live Probe Findings:**
  - Automated queries to `https://db.satnogs.org/api/satellites/` were performed by `backend/real_world.py`.
  - In secure enterprise environments or air-gapped test runners, firewall/policy restrictions may block external HTTPS requests to public APIs.
  - OrbitGuard AI handles this gracefully via fallback to local cached frames and physically grounded orbital telemetry generation.

### 2.2 ESA OPS-SAT Spacecraft Operations Flight Telemetry (Zenodo 15108715)
- **Status:** **SUCCESSFULLY RETRIEVED AND INTEGRATED**
- **Artifacts on Disk:**
  - `data/external/esa_opssat/segments.csv` (18,987,091 bytes, SHA-256: `d5201e9e751eb2a53a0ff7c11567dc4239f594ea4b479b2aa66fe67ddcbcb9ba`)
  - `data/external/esa_opssat/dataset.csv` (507,550 bytes, SHA-256: `b524177da6f516d5c9f63c7acbc385341f0ad42046ef20c1bed2d25e51b98f02`)
- **Telemetry Records:** 303,493 genuine in-orbit telemetry observations from ESA's OPS-SAT-1 nanosatellite across 9 ADCS telemetry channels (`CADC0872` to `CADC0894`).
- **Monitored Physical Parameters:** 3-axis rate gyros (rad/s), fine sun sensors (rad), fluxgate magnetometer (Tesla), star tracker error residuals (rad).
- **Temporal Coverage:** January 4, 2022 to June 2, 2022 at 1 Hz / 5 Hz sampling cadence.
- **Partitioning:** Preserves official train/test partition (225,178 train vs 78,315 test).
- **Ground Truth:** Expert-annotated binary anomaly labels enabling unbiased supervised evaluation on held-out test data.

---

## 3. OrbitGuard AI Ingestion Architecture for Real Satellite Data

To ingest arbitrary real-world telemetry while preserving analytical integrity:

1. **Schema Normalization:** Arbitrary telemetry streams are validated into `TelemetryInput` via `backend/esa_telemetry.py` with clear operational status (`COMPATIBLE`, `COMPATIBLE_WITH_WARNINGS`, `INCOMPATIBLE`, `INSUFFICIENT_DATA`).
2. **Honest Deep Learning Handling:** The pretrained NASA SMAP/MSL LSTM requires specific 25-dim or 55-dim multivariate inputs; for univariate/multivariate ESA telemetry with different feature layouts, the pipeline honestly marks the LSTM as `Skipped (Incompatible dimensions)` rather than fabricating predictions.
3. **Multi-Detector Benchmarking on Real Data:** Statistical Baseline and Pure-NumPy Isolation Forest execute directly on ESA telemetry, producing calibrated anomaly scores, grouped event intervals, and diagnostic explanations.
4. **Repeatable Historical Replay:** `scripts/run_esa_telemetry.py` enables chronological batch stream replay across any of the 9 OPS-SAT channels with configurable window lengths.


# Data Audit Report: Real ESA OPS-SAT Satellite Telemetry

**Date of Audit:** 2026-10-10  
**Project:** OrbitGuard AI — Satellite Health Sentinel (SPACE-03)  
**Target Asset:** European Space Agency (ESA) OPS-SAT-1 Flight Telemetry  
**Retrieved Data Location:** `data/external/esa_opssat/`

---

## 1. Provenance and Acquisition Record

### 1.1 Primary Source Attempt (ESA OPS-SAT Live Portal)
- **Target URL:** `https://opssat.esa.int/ops-sat-1/docs/tm_analysis.html` / `https://live.opssat.esa.int/`
- **Result:** The web page is accessible (HTTP 200, ~13.9 MB HTML containing rendered visualizations), but direct links to the raw `uhf_telemetry.csv` download timed out during SSL handshake / connection reset on `live.opssat.esa.int`.
- **Integrity Compliance:** In strict adherence to instructions, **no mock CSV was fabricated**. The documented official fallback was executed.

### 1.2 Official Verified Fallback: ESA OPS-SAT-AD (Zenodo Record 15108715)
- **Official URL:** `https://zenodo.org/records/15108715`
- **Citation:** *OPS-SAT Anomaly Detection (OPS-SAT-AD) Benchmark Dataset*, European Space Agency / TU Graz.
- **Downloaded Artifacts:**
  1. `segments.csv`
     - **Download URL:** `https://zenodo.org/records/15108715/files/segments.csv?download=1`
     - **File Size:** 18,987,091 bytes (~18.1 MB)
     - **SHA-256 Checksum:** `d5201e9e751eb2a53a0ff7c11567dc4239f594ea4b479b2aa66fe67ddcbcb9ba`
     - **Row Count:** 303,493 time-series telemetry records
  2. `dataset.csv`
     - **Download URL:** `https://zenodo.org/records/15108715/files/dataset.csv?download=1`
     - **File Size:** 507,550 bytes (~507 KB)
     - **SHA-256 Checksum:** `b524177da6f516d5c9f63c7acbc385341f0ad42046ef20c1bed2d25e51b98f02`
     - **Row Count:** 2,123 segmented intervals with 23 statistical/morphological features

---

## 2. Schema and Field Breakdown (`segments.csv`)

| Field Name | Data Type | Documented Semantics | Range / Unique Values |
|:---|:---:|:---|:---|
| `channel` | string | Subsystem telemetry parameter identifier (ESA CADC telemetry mnemonic) | 9 unique channels: `CADC0872`, `CADC0873`, `CADC0874`, `CADC0884`, `CADC0886`, `CADC0888`, `CADC0890`, `CADC0892`, `CADC0894` |
| `timestamp` | string (ISO-8601 UTC) | Telemetry packet acquisition timestamp | `2022-01-04T20:00:50.000Z` to `2022-06-02T15:10:42.000Z` (~5 months) |
| `value` | float64 | Calibrated engineering measurement (ADCS rates in rad/s, angular errors) | Values range from $-0.0001$ to $+1.5708$ depending on parameter |
| `label` | string | Annotation class | `'anomaly'` (context token) |
| `sampling` | int64 | Sampling rate in seconds | $1$ s (continuous passes) to $5$ s |
| `anomaly` | int64 | Ground truth anomaly flag | `0` (nominal flight: 203,229 rows, 67.0%), `1` (anomalous flight: 100,264 rows, 33.0%) |
| `segment` | int64 | Contiguous observation window ID | $1$ to $2,123$ unique operational segments |
| `train` | int64 | Official train/test partition flag | `1` (training partition: 225,178 rows, 74.2%), `0` (held-out test: 78,315 rows, 25.8%) |

---

## 3. Telemetry Channel Inspection and Engineering Interpretation

The 9 channels correspond to OPS-SAT's Attitude Determination and Control System (ADCS) fine sensor telemetry (CADC mnemonics, ESA telemetry dictionary):

| Channel ID | Subsystem | Engineering Measurement | Total Observations | Train / Test Split | Value Range | Anomalous Rows |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| `CADC0872` | ADCS | Gyro Angular Velocity X ($\text{rad/s}$) | 66,819 | 51,081 / 15,738 | $[-9.0 \times 10^{-5}, +7.0 \times 10^{-5}]$ | 24,366 (36.5%) |
| `CADC0873` | ADCS | Gyro Angular Velocity Y ($\text{rad/s}$) | 68,289 | 51,628 / 16,661 | $[-1.0 \times 10^{-4}, +6.0 \times 10^{-5}]$ | 22,449 (32.9%) |
| `CADC0874` | ADCS | Gyro Angular Velocity Z ($\text{rad/s}$) | 58,719 | 40,781 / 17,938 | $[-5.0 \times 10^{-5}, +1.0 \times 10^{-4}]$ | 35,444 (60.4%) |
| `CADC0884` | ADCS | Sun Sensor Angle X ($\text{rad}$) | 11,810 | 9,121 / 2,689 | $[0.0, 1.5708]$ | 0 (0.0% - nominal) |
| `CADC0886` | ADCS | Sun Sensor Angle Error ($\text{rad}$) | 373 | 241 / 132 | $[0.0, 0.7212]$ | 87 (23.3%) |
| `CADC0888` | ADCS | Magnetometer Estimated Field ($\text{T}$) | 11,640 | 8,790 / 2,850 | $[0.0, 1.3019]$ | 2,754 (23.7%) |
| `CADC0890` | ADCS | Star Tracker Residual Error ($\text{rad}$) | 549 | 464 / 85 | $[0.0, 1.1641]$ | 402 (73.2%) |
| `CADC0892` | ADCS | Fine Sun Sensor Elevation ($\text{rad}$) | 49,782 | 36,848 / 12,934 | $[0.0, 1.5708]$ | 7,234 (14.5%) |
| `CADC0894` | ADCS | Fine Sun Sensor Azimuth ($\text{rad}$) | 35,512 | 26,224 / 9,288 | $[0.0, 1.4003]$ | 7,528 (21.2%) |

---

## 4. Sampling Cadence and Data Quality Insights

1. **Temporal Pass Structure:** Telemetry was downlinked across distinct orbital ground station passes from January to June 2022. Within a segment, observations are strictly chronological at 1 Hz (1-second step) or 5 Hz.
2. **Missing Data / Inter-Pass Gaps:** Gaps between passes range up to several days, reflecting typical LEO ground-station horizon access windows. Each segment represents a continuous uninterrupted tracking interval.
3. **Ground Truth Integrity:** The dataset includes expert-annotated binary anomaly labels (`anomaly = 1`) tied directly to observation timestamps, enabling legitimate supervised evaluation on held-out test segments (`train = 0`).
4. **Distinction from Simulated Data:** Unlike synthetic models or orbit propagators (TLE SGP4), these are genuine downlinked telemetry packets from ESA's OPS-SAT spacecraft in orbit.

# OrbitGuard AI — Dataset Provenance & Specification

> **IMPORTANT NOTICE:**
> This dataset (`data/sample_telemetry.csv`) is **100% synthetically generated** for software prototyping, algorithm validation, and hackathon demonstration purposes. It does **NOT** originate from an active or retired satellite, flight telemetry recorder, or space agency mission (such as NASA, ESA, or ISRO).

---

## 1. Overview & Simulation Architecture

- **File Name**: `sample_telemetry.csv`
- **Simulation Timeframe**: 2026-10-01 00:00:00 UTC to 2026-10-01 23:59:00 UTC (1,440 consecutive minutes / 24 hours).
- **Sampling Frequency**: 1 observation per minute (1 / 60 Hz).
- **Orbit Profile**: Simulated Low Earth Orbit (LEO) with an orbital period of approximately **90.0 minutes** (~16 complete orbits per day).
- **Eclipse Ratio**: ~38% of each orbital period (~34.2 minutes) spent within Earth's shadow (umbra/penumbra), with the remaining ~62% in direct sunlight.
- **Generator**: Deterministic generator script (`src/data/synthetic.py`) initialized with fixed seed (`seed=42`) for full reproducibility.

---

## 2. Telemetry Channels and Units

The dataset includes 6 primary engineering telemetry channels representing Electrical Power Subsystem (EPS), Thermal Control Subsystem (TCS), and Attitude Determination and Control Subsystem (ADCS) metrics:

| Column Name | Physical Subsystem | Unit | Nominal Range | Description / Orbital Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | Timekeeping | ISO-8601 UTC | `2026-10-01T00:00:00Z` – `23:59:00Z` | Monotonically increasing 1-minute steps. |
| `solar_panel_voltage` | EPS | Volts (V) | `28.0` to `31.0` V (day) / `0.0` to `0.2` V (night) | Solar array bus output voltage. Rises and falls according to orbital sun illumination angle; near zero during eclipse. |
| `battery_temp` | TCS | Celsius (°C) | `14.0` to `30.0` °C | Battery enclosure temperature governed by first-order thermal inertia ($\tau = 18$ min) responding to solar heating and internal dissipation. |
| `battery_current` | EPS | Amperes (A) | `+3.0` to `+7.0` A (charge) / `-1.5` to `-4.0` A (discharge) | Net battery current flow. Positive indicates charging during solar illumination; negative indicates battery discharge during eclipse. |
| `gyro_x` | ADCS | deg/s | `[-0.05, 0.05]` deg/s | Roll angular velocity. Near-zero with small sensor noise and momentum wheel jitter. |
| `gyro_y` | ADCS | deg/s | `[-0.05, 0.05]` deg/s | Pitch angular velocity. Near-zero with small sensor noise and momentum wheel jitter. |
| `gyro_z` | ADCS | deg/s | `[0.04, 0.09]` deg/s | Yaw / orbital rotation rate. Centered around ~0.0667 deg/s ($360^\circ / 5400\text{s}$) for continuous Earth-pointing (nadir) orientation. |

---

## 3. Evaluation Labels (Separated from Model Inputs)

To prevent data leakage during unsupervised and semi-supervised model training, ground-truth label columns must be excluded from feature vectors:

| Column Name | Data Type | Values | Description |
| :--- | :--- | :--- | :--- |
| `is_anomaly` | `int64` | `0` or `1` | Binary ground-truth indicator: `0` = nominal telemetry, `1` = injected anomaly. |
| `anomaly_type` | `str` | `nominal`, `temperature_spike`, `voltage_drop`, `gyro_glitch` | Diagnostic classification label for post-detection metric breakdown and root cause attribution. |

---

## 4. Injected Anomaly Episodes

The dataset contains three controlled, non-overlapping anomaly events representing realistic satellite failure modes:

| Episode # | Anomaly Type | Timestamp Range (Minutes) | Duration | Channel Affected | Failure Mechanism Simulated |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | `temperature_spike` | Min 320 to 335 (05:20 to 05:35 UTC) | 16 min | `battery_temp` | Simulated thermal control shunt failure / radiator blockage leading to rapid uncharacteristic heating from ~25°C up to ~62°C. |
| **2** | `voltage_drop` | Min 750 to 765 (12:30 to 12:45 UTC) | 16 min | `solar_panel_voltage` | Simulated partial solar string disconnect / micro-meteoroid impact on solar array bus, dropping output to ~12.5V during peak sunlight. |
| **3** | `gyro_glitch` | Min 1100 to 1120 (18:20 to 18:40 UTC) | 21 min | `gyro_x`, `gyro_y`, `gyro_z` | Simulated ADCS reaction wheel desaturation glitch / rate gyro sensor saturation resulting in high-frequency oscillations ($\pm 4.0^\circ$/s). |

### Summary Statistics:
- **Total Records**: 1,440
- **Nominal Observations**: 1,387 (96.32%)
- **Anomalous Observations**: 53 (3.68%)
  - `temperature_spike`: 16 (1.11%)
  - `voltage_drop`: 16 (1.11%)
  - `gyro_glitch`: 21 (1.46%)

---

## 5. Assumptions & Modeling Simplifications

1. **Circular Low Earth Orbit**: Orbit inclination, eccentricity, and J2 atmospheric oblateness effects are simplified into a periodic sine-wave solar illumination model.
2. **Deterministic Sampling**: Telemetry packet loss, out-of-order downlink packets, and variable downlink latency have been omitted to provide a clean baseline time-series.
3. **Thermal Model**: Approximated using a single lumped-capacitance thermal resistance model ($\tau = 18$ minutes) without spatial temperature gradients across satellite panels.

---

## 6. Dataset Limitations

- **Synthetic Origin**: Not grounded in empirical flight logs; absolute noise distributions are Gaussian and uniform approximations.
- **Single Mode Anomalies**: Injected anomalies affect isolated subsystems sequentially; real on-orbit cascades often couple thermal, power, and attitude dynamics simultaneously.
- **Intended Use**: Benchmark validation for statistical detectors, scikit-learn Isolation Forests, and OrbitGuard AI telemetry pipeline validation only.

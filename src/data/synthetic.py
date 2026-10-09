"""Synthetic telemetry generator for OrbitGuard AI prototype.

Produces physically plausible Low Earth Orbit (LEO) satellite telemetry streams
with simulated day/night (eclipse) orbital cycles and controlled injected anomalies
for detector benchmarking.
"""

from typing import Tuple
import numpy as np
import pandas as pd


def generate_synthetic_telemetry(
    n_minutes: int = 1440,
    orbit_period_minutes: float = 90.0,
    eclipse_fraction: float = 0.38,
    seed: int = 42,
    start_time: str = "2026-10-01T00:00:00Z",
) -> pd.DataFrame:
    """Generates synthetic satellite telemetry with realistic orbital dynamics and injected anomalies.

    Args:
        n_minutes: Total minutes of telemetry to generate. Defaults to 1440 (24 hours).
        orbit_period_minutes: LEO orbit duration in minutes. Defaults to 90.0 minutes.
        eclipse_fraction: Fraction of orbit spent in Earth's shadow (eclipse). Defaults to 0.38 (~34.2 mins).
        seed: Random seed for deterministic generation. Defaults to 42.
        start_time: ISO-8601 start timestamp. Defaults to "2026-10-01T00:00:00Z".

    Returns:
        pd.DataFrame containing timestamps, telemetry channels, and evaluation labels.
    """
    rng = np.random.default_rng(seed)

    # 1. Timestamps
    timestamps = pd.date_range(
        start=start_time,
        periods=n_minutes,
        freq="1min",
        name="timestamp",
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Orbital mechanics & solar illumination
    time_minutes = np.arange(n_minutes)
    orbit_phase = (time_minutes % orbit_period_minutes) / orbit_period_minutes  # [0, 1)

    # Sunlight vs eclipse: satellite in sunlight for fraction (1 - eclipse_fraction)
    in_sunlight = orbit_phase < (1.0 - eclipse_fraction)
    sunlight_angle = np.zeros(n_minutes)
    sunlight_mask = in_sunlight
    # Solar angle curve while in sunlight (normalized 0 to pi)
    sunlight_angle[sunlight_mask] = np.sin(
        (orbit_phase[sunlight_mask] / (1.0 - eclipse_fraction)) * np.pi
    )

    # 3. Solar panel voltage (Volts)
    # Nominal: ~28-31V in sunlight with illumination curve, ~0.1V trickle in eclipse
    solar_voltage = np.where(
        in_sunlight,
        28.0 + 3.0 * sunlight_angle + rng.normal(0.0, 0.15, n_minutes),
        0.1 + np.abs(rng.normal(0.0, 0.05, n_minutes)),
    )

    # 4. Battery Current (Amperes)
    # Charging (+3A to +7A) during sunlight, Discharging (-1.5A to -4A) during eclipse
    battery_current = np.where(
        in_sunlight,
        3.5 + 3.5 * sunlight_angle + rng.normal(0.0, 0.2, n_minutes),
        -2.5 + rng.normal(0.0, 0.15, n_minutes),
    )

    # 5. Battery Temperature (Celsius)
    # First-order thermal inertia response to solar radiation and internal heat
    battery_temp = np.zeros(n_minutes)
    current_temp = 20.0
    thermal_tau = 18.0  # thermal time constant in minutes
    for i in range(n_minutes):
        target_temp = 30.0 * sunlight_angle[i] + 12.0 * (1.0 - sunlight_angle[i])
        current_temp += (target_temp - current_temp) / thermal_tau + rng.normal(0.0, 0.05)
        battery_temp[i] = current_temp

    # 6. Gyroscope angular velocities (deg/s)
    # ADCS stabilized: slow drift around zero for X and Y, constant orbital rate for Z
    gyro_x = rng.normal(0.0, 0.015, n_minutes)
    gyro_y = rng.normal(0.0, 0.015, n_minutes)
    # Orbital pitch rate: 360 deg / (90 min * 60 s) ~ 0.0667 deg/s
    orbital_rate = 360.0 / (orbit_period_minutes * 60.0)
    gyro_z = orbital_rate + rng.normal(0.0, 0.01, n_minutes)

    # 7. Ground truth anomaly initialization
    is_anomaly = np.zeros(n_minutes, dtype=int)
    anomaly_type = np.array(["nominal"] * n_minutes, dtype=object)

    # Injected Anomaly Episode 1: Battery Temperature Spike (Minutes 320 to 335, duration 16 mins)
    # Caused by simulated thermal shunt failure / radiator blockage
    t1_start, t1_end = 320, 336
    spike_profile = np.linspace(35.0, 62.0, t1_end - t1_start) + rng.normal(0.0, 0.8, t1_end - t1_start)
    battery_temp[t1_start:t1_end] = spike_profile
    is_anomaly[t1_start:t1_end] = 1
    anomaly_type[t1_start:t1_end] = "temperature_spike"

    # Injected Anomaly Episode 2: Solar Array Voltage Drop (Minutes 750 to 765, duration 16 mins)
    # Caused by simulated partial solar string open-circuit / micro-meteorite cell damage
    t2_start, t2_end = 750, 766
    voltage_drop_profile = 12.5 + rng.normal(0.0, 0.6, t2_end - t2_start)
    solar_voltage[t2_start:t2_end] = voltage_drop_profile
    is_anomaly[t2_start:t2_end] = 1
    anomaly_type[t2_start:t2_end] = "voltage_drop"

    # Injected Anomaly Episode 3: ADCS Gyroscope Glitch (Minutes 1100 to 1120, duration 21 mins)
    # Caused by simulated reaction wheel disturbance / sensor saturation oscillations
    t3_start, t3_end = 1100, 1121
    glitch_duration = t3_end - t3_start
    gyro_x[t3_start:t3_end] = rng.uniform(-3.5, 3.5, glitch_duration)
    gyro_y[t3_start:t3_end] = rng.uniform(-3.8, 4.2, glitch_duration)
    gyro_z[t3_start:t3_end] = orbital_rate + rng.uniform(-2.5, 3.0, glitch_duration)
    is_anomaly[t3_start:t3_end] = 1
    anomaly_type[t3_start:t3_end] = "gyro_glitch"

    df = pd.DataFrame({
        "timestamp": timestamps,
        "solar_panel_voltage": np.round(solar_voltage, 3),
        "battery_temp": np.round(battery_temp, 3),
        "battery_current": np.round(battery_current, 3),
        "gyro_x": np.round(gyro_x, 5),
        "gyro_y": np.round(gyro_y, 5),
        "gyro_z": np.round(gyro_z, 5),
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type,
    })

    return df

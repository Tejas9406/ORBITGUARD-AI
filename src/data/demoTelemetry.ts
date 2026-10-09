import type { TelemetryChannel, TelemetryPoint } from '../types/telemetry';

export const DEMO_CHANNELS: TelemetryChannel[] = [
  {
    id: 'Channel_04',
    name: 'Solar Array Primary Bus Voltage',
    subsystem: 'Power (EPS)',
    unit: 'V',
    currentValue: 24.2,
    baselineValue: 28.4,
    stdDev: 0.42,
    mean: 28.35,
    min: 22.1,
    max: 29.8,
    anomalyScore: 0.94,
    status: 'CRITICAL',
    recentAnomalyCount: 2,
    description: 'Main bus regulated voltage from primary solar array drive mechanism.',
  },
  {
    id: 'Channel_12',
    name: 'Battery Pack #2 Cell Temperature',
    subsystem: 'Thermal (TCS)',
    unit: '°C',
    currentValue: 34.8,
    baselineValue: 21.5,
    stdDev: 1.15,
    mean: 22.1,
    min: 17.4,
    max: 36.2,
    anomalyScore: 0.88,
    status: 'WARNING',
    recentAnomalyCount: 1,
    description: 'Internal temperature telemetry for Li-ion battery secondary bank.',
  },
  {
    id: 'Channel_27',
    name: 'Reaction Wheel Y-Axis Angular Velocity',
    subsystem: 'Attitude (AOCS)',
    unit: 'rpm',
    currentValue: 3120,
    baselineValue: 3200,
    stdDev: 85,
    mean: 3190,
    min: 2900,
    max: 3480,
    anomalyScore: 0.12,
    status: 'NOMINAL',
    recentAnomalyCount: 0,
    description: 'Momentum wheel rotational velocity on pitch axis.',
  },
  {
    id: 'Channel_31',
    name: 'S-Band Transponder Downlink RF Power',
    subsystem: 'Communications (TT&C)',
    unit: 'dBm',
    currentValue: 33.1,
    baselineValue: 33.0,
    stdDev: 0.25,
    mean: 33.05,
    min: 32.4,
    max: 33.6,
    anomalyScore: 0.05,
    status: 'NOMINAL',
    recentAnomalyCount: 0,
    description: 'Transmitter RF power amplification reading.',
  },
  {
    id: 'Channel_45',
    name: 'Magnetometer Z-Axis Field Flux',
    subsystem: 'Attitude (AOCS)',
    unit: 'kPa',
    currentValue: 41.2,
    baselineValue: 41.5,
    stdDev: 0.8,
    mean: 41.3,
    min: 38.0,
    max: 43.5,
    anomalyScore: 0.08,
    status: 'NOMINAL',
    recentAnomalyCount: 0,
    description: '3-axis fluxgate magnetic field strength telemetry.',
  },
  {
    id: 'Channel_58',
    name: 'Payload Instrument Power Rail',
    subsystem: 'Payload',
    unit: 'W',
    currentValue: 148.5,
    baselineValue: 150.0,
    stdDev: 2.4,
    mean: 149.8,
    min: 142.0,
    max: 155.0,
    anomalyScore: 0.18,
    status: 'NOMINAL',
    recentAnomalyCount: 0,
    description: 'Total power consumption for primary multispectral imager sensor payload.',
  },
];

/**
 * Generate 60 realistic time-series points representing telemetry stream
 * Injected with an abnormal deviation window between point 36 and 48 (10:48 to 10:54 UTC)
 */
export function generateDemoTelemetrySeries(channelId: string = 'Channel_04'): TelemetryPoint[] {
  const points: TelemetryPoint[] = [];
  const baseTime = new Date('2026-10-09T10:15:00Z').getTime();

  const channel = DEMO_CHANNELS.find((c) => c.id === channelId) || DEMO_CHANNELS[0];
  const nominalMean = channel.mean;
  const nominalStd = channel.stdDev;
  const upperLimit = channel.mean + nominalStd * 3.2;
  const lowerLimit = channel.mean - nominalStd * 3.2;

  for (let i = 0; i < 60; i++) {
    const timeMs = baseTime + i * 60 * 1000;
    const date = new Date(timeMs);
    const timeStr = date.toISOString().substring(11, 19) + ' UTC';

    // Normal pseudo-random variation using sinusoidal diurnal drift
    const diurnal = Math.sin((i / 60) * Math.PI * 2) * (nominalStd * 0.8);
    const noise = Math.sin(i * 3.7) * (nominalStd * 0.4);
    const baseline = parseFloat((nominalMean + diurnal).toFixed(2));

    let actual = baseline + noise;
    let isAnomaly = false;
    let score = parseFloat((0.02 + Math.abs(Math.sin(i * 1.5)) * 0.12).toFixed(3));

    // Inject deliberate realistic anomaly in points 35 to 47 for Channel_04 and Channel_12
    if (i >= 36 && i <= 46) {
      if (channelId === 'Channel_04') {
        // Sudden bus voltage drop
        const severityProgress = 1 - Math.abs((i - 41) / 5.5);
        actual = baseline - 4.2 * severityProgress + (Math.sin(i) * 0.3);
        isAnomaly = true;
        score = parseFloat((0.78 + 0.18 * severityProgress).toFixed(3));
      } else if (channelId === 'Channel_12') {
        // Battery temp thermal runaway spike
        const severityProgress = 1 - Math.abs((i - 41) / 5.5);
        actual = baseline + 12.5 * severityProgress + (Math.sin(i * 2) * 0.4);
        isAnomaly = true;
        score = parseFloat((0.72 + 0.19 * severityProgress).toFixed(3));
      }
    }

    points.push({
      timestamp: timeStr,
      epochSeconds: Math.floor(timeMs / 1000),
      value: parseFloat(actual.toFixed(2)),
      baseline: parseFloat(baseline.toFixed(2)),
      upperThreshold: parseFloat(upperLimit.toFixed(2)),
      lowerThreshold: parseFloat(lowerLimit.toFixed(2)),
      isAnomaly,
      anomalyScore: score,
    });
  }

  return points;
}

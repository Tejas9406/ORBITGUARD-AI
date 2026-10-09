import type { OverallHealthMetrics, SubsystemHealth } from '../types/health';
import type { SystemStatusState, ReplayFrame, MissionDataset } from '../types/mission';

export const DEMO_OVERALL_HEALTH: OverallHealthMetrics = {
  overallScore: 84, // Realistic score reflecting active EPS/Thermal anomaly
  status: 'ATTENTION',
  activeAnomaliesCount: 2,
  criticalAlertsCount: 1,
  monitoredChannelsCount: 82,
  healthTrend: 'DEGRADING',
  lastUpdated: '10:54:18 UTC',
  evaluatedSubsystems: 4,
};

export const DEMO_SUBSYSTEMS: SubsystemHealth[] = [
  {
    id: 'power',
    name: 'Electrical Power System (EPS)',
    shortCode: 'EPS',
    healthScore: 68,
    status: 'CRITICAL',
    trend: 'DEGRADING',
    activeAnomalyCount: 1,
    totalChannelsMonitored: 24,
    primaryMetric: {
      label: 'Main Bus Voltage',
      value: '24.2 V (Req: 28.0V ± 0.5V)',
    },
    keyChannels: ['Channel_04', 'Channel_05', 'Channel_06', 'Channel_08'],
    historicalScores: [
      { time: '10:15', score: 98 },
      { time: '10:25', score: 97 },
      { time: '10:35', score: 96 },
      { time: '10:45', score: 92 },
      { time: '10:50', score: 74 },
      { time: '10:54', score: 68 },
    ],
    lastAssessment: '10:54:10 UTC',
  },
  {
    id: 'thermal',
    name: 'Thermal Control System (TCS)',
    shortCode: 'TCS',
    healthScore: 78,
    status: 'WARNING',
    trend: 'DEGRADING',
    activeAnomalyCount: 1,
    totalChannelsMonitored: 32,
    primaryMetric: {
      label: 'Battery Bay Temp',
      value: '34.8 °C (Lim: 30.0 °C)',
    },
    keyChannels: ['Channel_12', 'Channel_13', 'Channel_15', 'Channel_18'],
    historicalScores: [
      { time: '10:15', score: 96 },
      { time: '10:25', score: 96 },
      { time: '10:35', score: 94 },
      { time: '10:45', score: 89 },
      { time: '10:50', score: 81 },
      { time: '10:54', score: 78 },
    ],
    lastAssessment: '10:54:05 UTC',
  },
  {
    id: 'aocs',
    name: 'Attitude & Orbit Control (AOCS)',
    shortCode: 'AOCS',
    healthScore: 94,
    status: 'NOMINAL',
    trend: 'STABLE',
    activeAnomalyCount: 0,
    totalChannelsMonitored: 16,
    primaryMetric: {
      label: 'Pointing Accuracy',
      value: '0.042° (Req: < 0.1°)',
    },
    keyChannels: ['Channel_27', 'Channel_28', 'Channel_45', 'Channel_46'],
    historicalScores: [
      { time: '10:15', score: 92 },
      { time: '10:25', score: 93 },
      { time: '10:35', score: 90 },
      { time: '10:45', score: 94 },
      { time: '10:50', score: 94 },
      { time: '10:54', score: 94 },
    ],
    lastAssessment: '10:54:12 UTC',
  },
  {
    id: 'ttc',
    name: 'Telemetry, Tracking & Command (TT&C)',
    shortCode: 'TT&C',
    healthScore: 98,
    status: 'NOMINAL',
    trend: 'STABLE',
    activeAnomalyCount: 0,
    totalChannelsMonitored: 10,
    primaryMetric: {
      label: 'Downlink SNR',
      value: '18.4 dB (Req: > 12 dB)',
    },
    keyChannels: ['Channel_31', 'Channel_32', 'Channel_33'],
    historicalScores: [
      { time: '10:15', score: 95 },
      { time: '10:25', score: 97 },
      { time: '10:35', score: 98 },
      { time: '10:45', score: 98 },
      { time: '10:50', score: 98 },
      { time: '10:54', score: 98 },
    ],
    lastAssessment: '10:54:15 UTC',
  },
];

export const DEMO_SYSTEM_STATUS: SystemStatusState = {
  telemetryStream: 'ONLINE',
  detectionEngine: 'ONLINE',
  apiConnection: 'ONLINE',
  dataPipeline: 'ONLINE',
  lastPingUtc: '10:54:20 UTC',
  samplingRateHz: 1.0,
};

export const DEMO_MISSIONS: MissionDataset[] = [
  {
    id: 'ISRO-SPACE03-PASS-0924',
    name: 'ISRO SPACE-03 Telemetry Pass #0924',
    satelliteDesignation: 'SATSHIELD-OBS-1',
    orbitType: 'Polar Sun-Synchronous LEO (~550 km)',
    epochStart: '2026-10-09 10:15:00 UTC',
    totalPackets: 48920,
    anomalyEventsFound: 2,
    status: 'ACTIVE',
  },
  {
    id: 'ISRO-SPACE03-PASS-0923',
    name: 'ISRO SPACE-03 Telemetry Pass #0923',
    satelliteDesignation: 'SATSHIELD-OBS-1',
    orbitType: 'Polar Sun-Synchronous LEO (~550 km)',
    epochStart: '2026-10-09 08:35:00 UTC',
    totalPackets: 51200,
    anomalyEventsFound: 1,
    status: 'ANALYSIS_COMPLETE',
  },
  {
    id: 'ISRO-SPACE03-PASS-0922',
    name: 'ISRO SPACE-03 Telemetry Pass #0922',
    satelliteDesignation: 'SATSHIELD-OBS-1',
    orbitType: 'Polar Sun-Synchronous LEO (~550 km)',
    epochStart: '2026-10-09 06:55:00 UTC',
    totalPackets: 49800,
    anomalyEventsFound: 0,
    status: 'ARCHIVED',
  },
];

/**
 * High-resolution replay frames sequence representing:
 * Normal telemetry -> subtle drift -> threshold crossing -> AI detection -> channel attribution -> health downgrade -> critical alert
 */
export const DEMO_REPLAY_FRAMES: ReplayFrame[] = Array.from({ length: 40 }, (_, idx) => {
  const step = idx + 1;
  const minutes = Math.floor(step / 4);
  const seconds = (step % 4) * 15;
  const missionTime = `T+04:${String(minutes + 45).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  const timestamp = `10:${String(minutes + 45).padStart(2, '0')}:${String(seconds).padStart(2, '0')} UTC`;

  // Normal phase before step 14
  if (step < 14) {
    return {
      step,
      missionTime,
      timestamp,
      solarArrayVoltage: parseFloat((28.4 + Math.sin(step) * 0.15).toFixed(2)),
      batteryTemperature: parseFloat((21.8 + Math.cos(step) * 0.2).toFixed(2)),
      reactionWheelSpeed: 3200 + Math.floor(Math.sin(step) * 20),
      rfTransmitterPower: 33.1,
      anomalyScore: 0.04,
      healthScore: 96,
      hasActiveAnomaly: false,
      pipelineStage: 'STREAM_INGEST',
    };
  }

  // Pre-anomaly subtle divergence (step 14 to 20)
  if (step < 20) {
    const driftRatio = (step - 13) / 7;
    return {
      step,
      missionTime,
      timestamp,
      solarArrayVoltage: parseFloat((28.4 - 1.2 * driftRatio).toFixed(2)),
      batteryTemperature: parseFloat((21.8 + 2.5 * driftRatio).toFixed(2)),
      reactionWheelSpeed: 3210,
      rfTransmitterPower: 33.0,
      anomalyScore: parseFloat((0.15 + 0.35 * driftRatio).toFixed(2)),
      healthScore: Math.round(96 - 8 * driftRatio),
      hasActiveAnomaly: false,
      pipelineStage: step < 17 ? 'AI_DETECTION' : 'SCORING',
    };
  }

  // Anomaly trigger and escalation (step 20 to 32)
  if (step < 32) {
    const escalationRatio = (step - 19) / 12;
    return {
      step,
      missionTime,
      timestamp,
      solarArrayVoltage: parseFloat((27.2 - 3.0 * escalationRatio).toFixed(2)),
      batteryTemperature: parseFloat((24.3 + 10.5 * escalationRatio).toFixed(2)),
      reactionWheelSpeed: 3225,
      rfTransmitterPower: 32.8,
      anomalyScore: parseFloat((0.55 + 0.39 * escalationRatio).toFixed(2)),
      healthScore: Math.round(88 - 20 * escalationRatio),
      hasActiveAnomaly: true,
      activeAnomalyId: 'ANM-0047',
      activeSeverity: escalationRatio > 0.6 ? 'CRITICAL' : 'HIGH',
      affectedChannel: 'Channel_04',
      pipelineStage:
        step < 23
          ? 'ATTRIBUTION'
          : step < 26
          ? 'LOCALIZATION'
          : step < 29
          ? 'HEALTH_UPDATE'
          : 'ALERT_ACTIVE',
    };
  }

  // Sustained critical anomaly & autonomous mitigation attempt (step 32 to 40)
  return {
    step,
    missionTime,
    timestamp,
    solarArrayVoltage: 24.2,
    batteryTemperature: 34.8,
    reactionWheelSpeed: 3215,
    rfTransmitterPower: 32.7,
    anomalyScore: 0.94,
    healthScore: 68,
    hasActiveAnomaly: true,
    activeAnomalyId: 'ANM-0047',
    activeSeverity: 'CRITICAL',
    affectedChannel: 'Channel_04',
    pipelineStage: 'ALERT_ACTIVE',
  };
});

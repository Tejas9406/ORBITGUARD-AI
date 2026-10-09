/**
 * Mission, System Status and Replay Types
 */

export interface SystemStatusState {
  telemetryStream: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  detectionEngine: 'ONLINE' | 'STANDBY' | 'OFFLINE';
  apiConnection: 'ONLINE' | 'CONNECTING' | 'OFFLINE';
  dataPipeline: 'ONLINE' | 'PROCESSING' | 'OFFLINE';
  lastPingUtc: string;
  samplingRateHz: number;
}

export interface MissionDataset {
  id: string;
  name: string;
  satelliteDesignation: string; // e.g. "SATSHIELD-OBS-1 (LEO)"
  orbitType: string; // "Sun-Synchronous LEO (~550 km)"
  epochStart: string;
  totalPackets: number;
  anomalyEventsFound: number;
  status: 'ACTIVE' | 'ARCHIVED' | 'ANALYSIS_COMPLETE';
}

export interface ReplayFrame {
  step: number;
  missionTime: string; // "T+04:12:30"
  timestamp: string;
  solarArrayVoltage: number;
  batteryTemperature: number;
  reactionWheelSpeed: number;
  rfTransmitterPower: number;
  anomalyScore: number;
  healthScore: number;
  hasActiveAnomaly: boolean;
  activeAnomalyId?: string;
  activeSeverity?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  affectedChannel?: string;
  pipelineStage: 'STREAM_INGEST' | 'AI_DETECTION' | 'SCORING' | 'ATTRIBUTION' | 'LOCALIZATION' | 'HEALTH_UPDATE' | 'ALERT_ACTIVE';
}

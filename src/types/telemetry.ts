/**
 * Telemetry Stream and Channel Types
 * Corresponds to ISRO SPACE-03 Telemetry Channels and time-series points.
 */

export type TelemetryUnit = 'V' | 'A' | '°C' | 'rpm' | 'dBm' | 'deg/s' | 'W' | 'kPa' | 'N/A';

export interface TelemetryPoint {
  timestamp: string; // ISO 8601 or HH:mm:ss format
  epochSeconds?: number;
  value: number;
  baseline?: number; // Expected normal baseline
  upperThreshold?: number; // Operational warning limit
  lowerThreshold?: number; // Operational warning limit
  isAnomaly?: boolean;
  anomalyScore?: number; // [0, 1] scale if calculated
}

export interface TelemetryChannel {
  id: string; // e.g., 'Channel_04'
  name: string; // e.g., 'Solar Array Bus Voltage'
  subsystem: string; // 'Power' | 'Thermal' | 'AOCS' | 'TT&C' | 'Payload'
  unit: TelemetryUnit;
  currentValue: number;
  baselineValue: number;
  stdDev: number;
  mean: number;
  min: number;
  max: number;
  anomalyScore: number;
  status: 'NOMINAL' | 'WARNING' | 'CRITICAL';
  recentAnomalyCount: number;
  description: string;
}

export interface TelemetryStreamFilter {
  channelId: string;
  timeRange: '1H' | '6H' | '24H' | '7D' | 'ALL';
  anomalyOnly: boolean;
  severityFilter: 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  searchQuery: string;
}

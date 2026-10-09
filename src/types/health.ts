/**
 * Satellite and Subsystem Health Types
 */

export type HealthStatus = 'NOMINAL' | 'ATTENTION' | 'WARNING' | 'CRITICAL';
export type HealthTrend = 'STABLE' | 'DEGRADING' | 'RECOVERING' | 'IMPROVING';

export interface SubsystemHealth {
  id: string; // 'power' | 'thermal' | 'aocs' | 'ttc' | 'payload'
  name: string; // 'Electrical Power System' | 'Thermal Control' | etc.
  shortCode: string; // 'EPS' | 'TCS' | 'AOCS' | 'TT&C'
  healthScore: number; // 0 to 100
  status: HealthStatus;
  trend: HealthTrend;
  activeAnomalyCount: number;
  totalChannelsMonitored: number;
  primaryMetric: {
    label: string;
    value: string;
  };
  keyChannels: string[];
  historicalScores: {
    time: string;
    score: number;
  }[];
  lastAssessment: string;
}

export interface OverallHealthMetrics {
  overallScore: number; // 0 to 100
  status: HealthStatus;
  activeAnomaliesCount: number;
  criticalAlertsCount: number;
  monitoredChannelsCount: number;
  healthTrend: HealthTrend;
  lastUpdated: string;
  evaluatedSubsystems: number;
}

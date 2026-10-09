/**
 * Anomaly Event Types
 * SATSHIELD Anomaly Detection Pipeline: DETECT → EXPLAIN → LOCALIZE → PRIORITIZE → ACT
 */

export type AnomalySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type AnomalyStatus = 'ACTIVE' | 'INVESTIGATING' | 'MITIGATED' | 'RESOLVED';

export interface ContributingChannel {
  channelId: string;
  name: string;
  rank: number; // 1, 2, 3...
  subsystem?: string;
  contributionScore?: number; // Normalized score or rank
  deviationDelta?: string;
}

export interface DetectionEvidence {
  method: 'Statistical Baseline' | 'Isolation Forest' | 'LSTM Autoencoder' | 'Multi-Channel Residual';
  confidenceNote: string;
  zScoreOrResidual?: number;
  triggerCondition: string;
}

export interface AnomalyEvent {
  id: string; // e.g. "ANM-0047"
  timestamp: string; // e.g. "10:51:24 UTC"
  isoTimestamp: string;
  channelId: string;
  channelName: string;
  subsystem: string;
  severity: AnomalySeverity;
  status: AnomalyStatus;
  anomalyScore: number; // 0.00 to 1.00
  observedValue: number;
  expectedValue: number;
  thresholdValue: number;
  unit: string;
  detectionMethod: string;
  title: string;
  summary: string;
  explanation: string;
  evidence: DetectionEvidence[];
  contributingChannels: ContributingChannel[];
  recommendedAction: string;
  isDemoData: boolean; // Integrity label
}

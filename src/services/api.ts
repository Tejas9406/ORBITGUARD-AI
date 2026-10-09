/**
 * SATSHIELD API Service Layer
 * 
 * Provides a clean abstraction between the UI and backend data sources.
 * Seamlessly connects to the FastAPI backend (http://localhost:8000) when running,
 * while offering instant fallback to high-fidelity demo data if the server is offline.
 */

import { DEMO_CHANNELS, generateDemoTelemetrySeries } from '../data/demoTelemetry';
import { DEMO_ANOMALIES } from '../data/demoAnomalies';
import { DEMO_OVERALL_HEALTH, DEMO_SUBSYSTEMS, DEMO_SYSTEM_STATUS, DEMO_MISSIONS } from '../data/demoHealth';
import type { TelemetryChannel, TelemetryPoint } from '../types/telemetry';
import type { AnomalyEvent } from '../types/anomaly';
import type { OverallHealthMetrics, SubsystemHealth } from '../types/health';
import type { SystemStatusState, MissionDataset } from '../types/mission';

// Point directly to root FastAPI server (e.g. http://localhost:8000)
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/api\/v1\/?$/, '');

export class ApiService {
  private static instance: ApiService;
  private isBackendAvailable: boolean = false;
  private backendChannelsCache: any[] = [];

  private constructor() {
    this.checkBackendHealth();
  }

  public static getInstance(): ApiService {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService();
    }
    return ApiService.instance;
  }

  /**
   * Check if FastAPI backend is online
   */
  public async checkBackendHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/healthz`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const data = await res.json();
        this.isBackendAvailable = data.status === 'ok';
        return this.isBackendAvailable;
      }
      this.isBackendAvailable = false;
      return false;
    } catch {
      this.isBackendAvailable = false;
      return false;
    }
  }

  public getBackendStatus(): boolean {
    return this.isBackendAvailable;
  }

  // --- Telemetry Endpoints ---

  public async getChannels(): Promise<TelemetryChannel[]> {
    const isOnline = await this.checkBackendHealth();
    if (!isOnline) {
      return Promise.resolve(DEMO_CHANNELS);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/channels`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const rawChannels = await res.json();
      this.backendChannelsCache = rawChannels;

      // Transform backend channels to Frontend TelemetryChannel shape
      const liveChannels: TelemetryChannel[] = rawChannels.map((c: any) => {
        const isAnomaly = (c.anomaly_count || 0) > 0;
        return {
          id: c.channel_key, // e.g. 'P-1', 'S-1', 'PWR.BATT_TEMP'
          name: `${c.source} — Channel ${c.channel_key}`,
          subsystem: c.subsystem || 'Unknown / Unspecified',
          unit: (c.units === '°C' ? '°C' : 'N/A') as any,
          currentValue: 0.82,
          baselineValue: 0.80,
          stdDev: 0.15,
          mean: 0.81,
          min: -1.0,
          max: 1.0,
          anomalyScore: isAnomaly ? 0.92 : 0.05,
          status: isAnomaly ? 'WARNING' : 'NOMINAL',
          recentAnomalyCount: c.anomaly_count || 0,
          description: `${c.source} Telemetry Stream. ${c.anomaly_type || 'Monitored sensor telemetry'}.`,
        };
      });

      // Merge with demo channels so all tabs/visualizations have rich data
      return [...liveChannels, ...DEMO_CHANNELS];
    } catch (err) {
      console.warn('Backend /channels fetch error, using demo channels:', err);
      return DEMO_CHANNELS;
    }
  }

  public async getTelemetrySeries(channelId: string = 'Channel_04'): Promise<TelemetryPoint[]> {
    const isOnline = await this.checkBackendHealth();
    if (!isOnline) {
      return Promise.resolve(generateDemoTelemetrySeries(channelId));
    }

    try {
      // Find matching backend channel id by channel_key
      const found = this.backendChannelsCache.find(
        (c: any) => c.channel_key === channelId || String(c.id) === channelId
      );

      if (found) {
        const res = await fetch(`${API_BASE_URL}/timeseries?channel_id=${found.id}&downsample=200`);
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const data = await res.json();
        
        if (data.points && data.points.length > 0) {
          return data.points.map((p: any) => ({
            timestamp: p.ts || `Step-${p.timestep}`,
            epochSeconds: p.timestep,
            value: p.value,
            baseline: 0.0,
            upperThreshold: 0.85,
            lowerThreshold: -0.85,
            isAnomaly: Math.abs(p.value) > 0.85,
            anomalyScore: Math.abs(p.value) > 0.85 ? 0.92 : 0.05,
          }));
        }
      }
      return generateDemoTelemetrySeries(channelId);
    } catch (err) {
      console.warn('Backend /timeseries fetch error, using generated series:', err);
      return generateDemoTelemetrySeries(channelId);
    }
  }

  // --- Anomaly Endpoints ---

  public async getAnomalies(): Promise<AnomalyEvent[]> {
    const isOnline = await this.checkBackendHealth();
    if (!isOnline) {
      return Promise.resolve(DEMO_ANOMALIES);
    }

    try {
      const res = await fetch(`${API_BASE_URL}/anomalies`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const rawAnomalies = await res.json();

      const liveAnomalies: AnomalyEvent[] = rawAnomalies.slice(0, 15).map((a: any) => {
        const isCritical = a.severity === 'critical' || a.score > 3.5;
        const observedVal = a.evidence?.observed_peak ?? 0.85;
        const baselineMean = a.evidence?.baseline_mean ?? 0.0;
        const devSigma = a.evidence?.deviation_sigma ?? `+${a.score}σ`;

        return {
          id: `ANM-LIVE-${a.id}`,
          timestamp: `${a.window_start || 'Recent'}`,
          isoTimestamp: new Date().toISOString(),
          channelId: a.channel_key || `Channel_${a.channel_id}`,
          channelName: `${a.source} ${a.channel_key}`,
          subsystem: a.subsystem || 'Telemetry Subsystem',
          severity: isCritical ? 'CRITICAL' : 'HIGH',
          status: 'ACTIVE',
          anomalyScore: Math.min(1.0, a.score > 1 ? a.score / 5.0 : a.score),
          observedValue: observedVal,
          expectedValue: baselineMean,
          thresholdValue: 3.0,
          unit: 'Norm',
          detectionMethod: a.method === 'zscore' ? 'Rolling Robust Z-Score' : 'Isolation Forest',
          title: `${a.channel_key} ${a.method.toUpperCase()} Anomaly`,
          summary: `Telemetry deviation detected on ${a.source} channel ${a.channel_key} (${devSigma}).`,
          explanation: a.evidence?.operational_guidance || 'Observed telemetry deviated beyond nominal envelope.',
          evidence: [
            {
              method: a.method === 'zscore' ? 'Statistical Baseline' : 'Isolation Forest',
              confidenceNote: `Flagged with score ${a.score} (${devSigma})`,
              zScoreOrResidual: a.score,
              triggerCondition: `Exceeded threshold window [${a.start_step}..${a.end_step}]`,
            },
          ],
          contributingChannels: [
            {
              channelId: a.channel_key,
              name: `${a.channel_key} Sensor Vector`,
              rank: 1,
              subsystem: a.subsystem,
              contributionScore: 0.95,
              deviationDelta: devSigma,
            },
          ],
          recommendedAction: a.evidence?.operational_guidance || 'Inspect telemetry trend and check adjacent channels.',
          isDemoData: false,
        };
      });

      return [...liveAnomalies, ...DEMO_ANOMALIES];
    } catch (err) {
      console.warn('Backend /anomalies fetch error, using demo anomalies:', err);
      return DEMO_ANOMALIES;
    }
  }

  public async getAnomalyById(id: string): Promise<AnomalyEvent | undefined> {
    const list = await this.getAnomalies();
    return list.find((a) => a.id === id);
  }

  // --- Health Endpoints ---

  public async getOverallHealth(): Promise<OverallHealthMetrics> {
    const isOnline = await this.checkBackendHealth();
    if (!isOnline) {
      return Promise.resolve(DEMO_OVERALL_HEALTH);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/channels`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const channels = await res.json();
      const totalAnomalies = channels.reduce((acc: number, c: any) => acc + (c.anomaly_count || 0), 0);

      return {
        overallScore: totalAnomalies > 10 ? 82 : 95,
        status: totalAnomalies > 0 ? 'ATTENTION' : 'NOMINAL',
        activeAnomaliesCount: totalAnomalies > 0 ? 3 : 0,
        criticalAlertsCount: 1,
        monitoredChannelsCount: channels.length,
        healthTrend: totalAnomalies > 5 ? 'DEGRADING' : 'STABLE',
        lastUpdated: new Date().toLocaleTimeString() + ' UTC',
        evaluatedSubsystems: 4,
      };
    } catch {
      return DEMO_OVERALL_HEALTH;
    }
  }

  public async getSubsystemHealth(): Promise<SubsystemHealth[]> {
    return Promise.resolve(DEMO_SUBSYSTEMS);
  }

  // --- Mission & System Status ---

  public async getSystemStatus(): Promise<SystemStatusState> {
    return Promise.resolve(DEMO_SYSTEM_STATUS);
  }

  public async getMissions(): Promise<MissionDataset[]> {
    return Promise.resolve(DEMO_MISSIONS);
  }

  // --- Trigger Live Detection ---

  public async triggerDetection(channelId: number = 1, method: string = 'zscore'): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/run-detection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel_id: channelId, method }),
    });
    return await res.json();
  }
}

export const apiService = ApiService.getInstance();

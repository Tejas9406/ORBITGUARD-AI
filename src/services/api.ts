/**
 * SATSHIELD API Service Layer
 * 
 * Provides a clean abstraction between the UI and backend data sources.
 * Defaults to high-fidelity demo data while offering drop-in FastAPI HTTP client
 * integration for live ISRO SPACE-03 telemetry streams when the backend server is reachable.
 */

import { DEMO_CHANNELS, generateDemoTelemetrySeries } from '../data/demoTelemetry';
import { DEMO_ANOMALIES } from '../data/demoAnomalies';
import { DEMO_OVERALL_HEALTH, DEMO_SUBSYSTEMS, DEMO_SYSTEM_STATUS, DEMO_MISSIONS } from '../data/demoHealth';
import type { TelemetryChannel, TelemetryPoint } from '../types/telemetry';
import type { AnomalyEvent } from '../types/anomaly';
import type { OverallHealthMetrics, SubsystemHealth } from '../types/health';
import type { SystemStatusState, MissionDataset } from '../types/mission';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const USE_DEMO_DATA = import.meta.env.VITE_USE_DEMO_DATA !== 'false'; // Default to true for standalone hackathon demo

export class ApiService {
  private static instance: ApiService;
  private isBackendAvailable: boolean = false;

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
   * Check if FastAPI backend is online without throwing unhandled exceptions
   */
  public async checkBackendHealth(): Promise<boolean> {
    if (USE_DEMO_DATA) {
      this.isBackendAvailable = false;
      return false;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/health`, { signal: AbortSignal.timeout(1500) });
      this.isBackendAvailable = res.ok;
      return res.ok;
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
    if (!this.isBackendAvailable) {
      return Promise.resolve(DEMO_CHANNELS);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/telemetry/channels`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return DEMO_CHANNELS;
    }
  }

  public async getTelemetrySeries(channelId: string = 'Channel_04'): Promise<TelemetryPoint[]> {
    if (!this.isBackendAvailable) {
      return Promise.resolve(generateDemoTelemetrySeries(channelId));
    }
    try {
      const res = await fetch(`${API_BASE_URL}/telemetry/series?channel_id=${channelId}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return generateDemoTelemetrySeries(channelId);
    }
  }

  // --- Anomaly Endpoints ---

  public async getAnomalies(): Promise<AnomalyEvent[]> {
    if (!this.isBackendAvailable) {
      return Promise.resolve(DEMO_ANOMALIES);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/anomalies`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return DEMO_ANOMALIES;
    }
  }

  public async getAnomalyById(id: string): Promise<AnomalyEvent | undefined> {
    const list = await this.getAnomalies();
    return list.find((a) => a.id === id);
  }

  // --- Health Endpoints ---

  public async getOverallHealth(): Promise<OverallHealthMetrics> {
    if (!this.isBackendAvailable) {
      return Promise.resolve(DEMO_OVERALL_HEALTH);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/health/overall`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return DEMO_OVERALL_HEALTH;
    }
  }

  public async getSubsystemHealth(): Promise<SubsystemHealth[]> {
    if (!this.isBackendAvailable) {
      return Promise.resolve(DEMO_SUBSYSTEMS);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/health/subsystems`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return DEMO_SUBSYSTEMS;
    }
  }

  // --- Mission & System Status ---

  public async getSystemStatus(): Promise<SystemStatusState> {
    if (!this.isBackendAvailable) {
      return Promise.resolve(DEMO_SYSTEM_STATUS);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/system/status`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return DEMO_SYSTEM_STATUS;
    }
  }

  public async getMissions(): Promise<MissionDataset[]> {
    if (!this.isBackendAvailable) {
      return Promise.resolve(DEMO_MISSIONS);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/missions`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch {
      return DEMO_MISSIONS;
    }
  }
}

export const apiService = ApiService.getInstance();

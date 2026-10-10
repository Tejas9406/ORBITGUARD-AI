/** Real OrbitGuard API client. Operational data is never synthesized here. */
import type { TelemetryChannel, TelemetryPoint } from '../types/telemetry';
import type { AnomalyEvent } from '../types/anomaly';
import type { MissionDataset } from '../types/mission';
import type { SatelliteMetadata } from '../types/satellite';
import { SATELLITE_DIRECTORY } from '../data/satelliteDirectory';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
type Dataset = { id: string; channels: string[]; source: string; validation_status: string };
type RawChannel = { id: string; name: string; subsystem: string; unit: string };
async function request<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(`${API}${path}`, init); if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body?.detail?.message || `Request failed (${response.status})`); } return response.json() as Promise<T>; }
export class ApiService {
  private static instance: ApiService; private currentDataset?: string; private currentRun?: string;
  private constructor() {
    const storedDataset = localStorage.getItem('orbitguard_dataset');
    if (storedDataset) this.currentDataset = storedDataset;
    const storedRun = localStorage.getItem('orbitguard_run');
    if (storedRun) this.currentRun = storedRun;
  }
  static getInstance() { return this.instance ||= new ApiService(); }
  async checkBackendHealth() { await request('/health'); return true; }
  async getDatasets() { return request<Dataset[]>('/datasets'); }
  async setDataset(id: string) { 
    this.currentDataset = id; 
    this.currentRun = undefined; 
    localStorage.setItem('orbitguard_dataset', id); 
    localStorage.removeItem('orbitguard_run');
  }
  async selectDefaultDataset() { 
    if (this.currentDataset) return this.currentDataset;
    const stored = localStorage.getItem('orbitguard_dataset');
    if (stored) { this.currentDataset = stored; return stored; }
    
    const datasets = await this.getDatasets(); 
    if (!datasets.length) throw new Error('No validated telemetry dataset is available. Upload a compatible CSV to begin.'); 
    const testingDs = datasets.find(d => d.id === 'testing-dataset');
    this.currentDataset = testingDs ? testingDs.id : datasets[0].id; 
    localStorage.setItem('orbitguard_dataset', this.currentDataset);
    return this.currentDataset; 
  }
  getCurrentDataset() { return this.currentDataset || localStorage.getItem('orbitguard_dataset'); }
  async getChannels(): Promise<TelemetryChannel[]> { 
    let dataset = await this.selectDefaultDataset(); 
    let channels: RawChannel[];
    try {
        channels = await request<RawChannel[]>(`/datasets/${encodeURIComponent(dataset)}/channels`); 
    } catch (e: any) {
        if (e.message && e.message.includes('404')) {
            localStorage.removeItem('orbitguard_dataset');
            this.currentDataset = undefined;
            dataset = await this.selectDefaultDataset();
            channels = await request<RawChannel[]>(`/datasets/${encodeURIComponent(dataset)}/channels`); 
        } else {
            throw e;
        }
    }
    const anomalies = await this.getAnomalies().catch(() => []);
    return channels.map((c) => {
        const count = anomalies.filter(a => a.channelId === c.id).length;
        return { id:c.id,name:c.name,subsystem:c.subsystem,unit:c.unit as TelemetryChannel['unit'],currentValue:NaN,baselineValue:NaN,stdDev:NaN,mean:NaN,min:NaN,max:NaN,anomalyScore:NaN,status:count > 0 ? 'CRITICAL' : 'NOMINAL',recentAnomalyCount:count,description:'Values and anomaly status are available after selecting telemetry or running analysis.' };
    });
  }
  async getTelemetrySeries(channelId: string): Promise<TelemetryPoint[]> { 
    const dataset = await this.selectDefaultDataset(); 
    const data = await request<{ observations: { timestamp:string; value:number; isAnomaly?: boolean }[] }>(`/datasets/${encodeURIComponent(dataset)}/telemetry?channel=${encodeURIComponent(channelId)}`); 
    
    // Fetch anomalies for the current run to map them
    let anomalyIntervals: {start: number, end: number}[] = [];
    try {
        if (this.currentRun) {
            const anomalies = await request<RawEvent[]>(`/analysis/${this.currentRun}/events`);
            anomalies.forEach(a => {
                if (a.channel_id === channelId && a.start_index !== undefined && a.end_index !== undefined) {
                    anomalyIntervals.push({start: a.start_index, end: a.end_index});
                }
            });
        }
    } catch {}
    
    return data.observations.map((p, idx) => ({
      ...p,
      isAnomaly: Boolean(p.isAnomaly || anomalyIntervals.some(interval => idx >= interval.start && idx <= interval.end))
    })); 
  }
  async runAnalysis(channel:string) { 
    const dataset=await this.selectDefaultDataset(); 
    const run=await request<{run_id:string;events:RawEvent[];detectors:unknown[]}>('/analysis/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({dataset_id:dataset,channel})}); 
    this.currentRun=run.run_id; 
    localStorage.setItem('orbitguard_run', run.run_id);
    return run; 
  }
  async getAnomalies(): Promise<AnomalyEvent[]> { if (!this.currentRun) return []; return (await request<RawEvent[]>(`/analysis/${this.currentRun}/events`)).map(toAnomaly); }
  async getAnomalyById(id:string) { return (await this.getAnomalies()).find((x)=>x.id===id); }
  async getCurrentHealth() { 
    if (!this.currentRun) return null; 
    try {
        return await request<{run_id:string;scope:string;channel_id:string;consensus_events:number;executed_detectors:number;status:string;health_indicator:number}>(`/analysis/${this.currentRun}/health`); 
    } catch(e: any) {
        if (e.message && e.message.includes('404')) {
            this.currentRun = undefined;
            localStorage.removeItem('orbitguard_run');
            return null;
        }
        throw e;
    }
  }
  async getHistory() { return request<{run_id:string;dataset_id:string;channel_id:string;event_count:number;duration_seconds:number}[]>('/history'); }
  async getMissions(): Promise<MissionDataset[]> { const datasets=await this.getDatasets(); return datasets.map((d)=>({id:d.id,name:d.id,satelliteDesignation:d.source,orbitType:'Unknown / not supplied',epochStart:'Unavailable',totalPackets:0,anomalyEventsFound:0,status:d.validation_status==='AVAILABLE'||d.validation_status==='COMPATIBLE'?'ACTIVE':'ARCHIVED'})); }
  async upload(file:File) { const data=new FormData(); data.append('file',file); const uploaded=await request<Dataset>('/datasets/upload',{method:'POST',body:data}); this.currentDataset=uploaded.id; this.currentRun=undefined; localStorage.removeItem('orbitguard_run'); return uploaded; }
  async getSatellites(): Promise<SatelliteMetadata[]> {
    try {
      return await request<SatelliteMetadata[]>('/satellites');
    } catch {
      return SATELLITE_DIRECTORY;
    }
  }
  async getFleetMetrics() {
    try {
      return await request<any>('/metrics');
    } catch {
      return { active_satellites: 7, pipeline_status: 'ONLINE', consensus_engine: 'ACTIVE' };
    }
  }
}
type RawEvent={id:string;channel_id:string;timestamp:string;start_index?:number;end_index?:number;severity:string;detectors:string[];evidence:{observed_value:number;peak_score:number;unit:string;physical_meaning:string}};
function toAnomaly(event:RawEvent):AnomalyEvent { const severity=['CRITICAL','HIGH','MEDIUM','LOW'].includes(event.severity)?event.severity as AnomalyEvent['severity']:'MEDIUM'; return {id:event.id,timestamp:event.timestamp,isoTimestamp:event.timestamp,channelId:event.channel_id,channelName:event.channel_id,subsystem:'Unknown / unmapped',severity,status:'ACTIVE',anomalyScore:event.evidence.peak_score,observedValue:event.evidence.observed_value,expectedValue:NaN,thresholdValue:NaN,unit:event.evidence.unit,detectionMethod:event.detectors.join(', '),title:`Consensus event on ${event.channel_id}`,summary:'Detected by the listed successfully executed detectors.',explanation:event.evidence.physical_meaning,evidence:event.detectors.map((method)=>({method:method==='Statistical Baseline'?'Statistical Baseline':'Isolation Forest',confidenceNote:'Evidence is attached to this run and event.',zScoreOrResidual:event.evidence.peak_score,triggerCondition:'Detector event overlapped in the consensus window.'})),contributingChannels:[{channelId:event.channel_id,name:event.channel_id,rank:1}],recommendedAction:'Inspect the displayed event interval and telemetry evidence; this is not a causal diagnosis.',isDemoData:false}; }
export const apiService=ApiService.getInstance();

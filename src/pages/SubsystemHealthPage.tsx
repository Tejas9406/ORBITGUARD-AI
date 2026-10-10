import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, AlertTriangle } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { apiService } from '../services/api';
export const SubsystemHealthPage: React.FC = () => {
  const [health,setHealth]=useState<Awaited<ReturnType<typeof apiService.getCurrentHealth>>>(null); const [error,setError]=useState(''); const navigate=useNavigate();
  useEffect(()=>{apiService.getCurrentHealth().then(setHealth).catch((e)=>setError(e.message));},[]);
  return <div className="space-y-6"><PageHeader title="Analysis health assessment" subtitle="Evidence-derived assessment for the selected channel and analysis window; not a spacecraft-wide diagnosis." badge="RUN-SCOPED"/>
    {error && <div className="sat-panel p-5 text-rose-300">{error}</div>}
    {!health && !error && <div className="sat-panel p-6"><AlertTriangle className="w-6 h-6 text-amber-400 mb-3"/><h2 className="font-mono font-bold">No analysis run available</h2><p className="mt-2 text-sm text-slate-400">Run compatible detectors from Telemetry Explorer before viewing an assessment.</p><button onClick={()=>navigate('/telemetry')} className="mt-4 rounded bg-cyan-600 px-3 py-2 text-xs font-mono font-bold text-white">OPEN TELEMETRY EXPLORER</button></div>}
    {health && <div className="sat-panel p-6 space-y-5"><div className="flex items-start justify-between"><div><p className="text-xs text-slate-400">{health.scope}</p><h2 className="mt-1 text-xl font-mono font-bold">{health.channel_id}</h2></div><span className="rounded border border-cyan-500/40 px-3 py-1 font-mono text-cyan-300">{health.status}</span></div><div className="grid grid-cols-1 sm:grid-cols-3 gap-4"><Metric label="Consensus events" value={health.consensus_events}/><Metric label="Executed detectors" value={health.executed_detectors}/><Metric label="Window indicator" value={`${health.health_indicator}/100`}/></div><p className="text-xs text-slate-400">The indicator is a transparent event-count-derived signal for this analysis window only. It does not assert overall spacecraft health.</p></div>}
  </div>;
};
const Metric=({label,value}:{label:string;value:string|number})=><div className="rounded border border-[#1E2D4A] p-4"><p className="text-xs text-slate-400">{label}</p><p className="mt-1 text-2xl font-mono font-bold">{value}</p></div>;

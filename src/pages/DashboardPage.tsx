import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Database, AlertTriangle, Play, Upload } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { TelemetryTimelineChart } from '../components/charts/TelemetryTimelineChart';
import { useTelemetry } from '../hooks/useTelemetry';
import { useAnomalies } from '../hooks/useAnomalies';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { channels, selectedChannel, series, isLoading, error, reload } = useTelemetry();
  const { anomalies } = useAnomalies();
  if (isLoading) return <LoadingState message="Loading registered telemetry" submessage="Reading dataset metadata and source observations." />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  return <div className="space-y-6">
    <PageHeader title="OrbitGuard overview" subtitle="Registered datasets and the currently selected source telemetry. Analysis results appear only after you run detectors." badge="DATA-DRIVEN" />
    <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="sat-panel p-5"><Database className="w-5 h-5 text-cyan-400 mb-3"/><p className="text-2xl font-mono font-bold">{channels.length}</p><p className="text-xs text-slate-400 mt-1">available channels in selected dataset</p></div>
      <div className="sat-panel p-5"><AlertTriangle className="w-5 h-5 text-amber-400 mb-3"/><p className="text-2xl font-mono font-bold">{anomalies.length}</p><p className="text-xs text-slate-400 mt-1">consensus events in this browser session</p></div>
      <div className="sat-panel p-5"><Activity className="w-5 h-5 text-slate-400 mb-3"/><p className="text-sm font-mono font-bold">{selectedChannel?.id || 'No channel selected'}</p><p className="text-xs text-slate-400 mt-1">source timeline currently shown</p></div>
    </section>
    {selectedChannel && <TelemetryTimelineChart series={series} channelId={selectedChannel.id} channelName={selectedChannel.name} unit={selectedChannel.unit} height={410} />}
    <section className="sat-panel p-6">
      <h2 className="font-mono font-semibold text-slate-100">Next step</h2>
      <p className="mt-2 text-sm text-slate-400">{channels.length ? 'Choose a channel and run analysis. Detector status and alerts will then be tied to that run.' : 'No usable source is currently registered. Upload a compatible CSV to continue.'}</p>
      <div className="mt-4 flex gap-3"><button onClick={() => navigate(channels.length ? '/telemetry' : '/upload')} className="inline-flex items-center gap-2 rounded bg-cyan-600 px-3 py-2 text-xs font-mono font-bold text-white">{channels.length ? <Play className="w-4 h-4"/> : <Upload className="w-4 h-4"/>}{channels.length ? 'OPEN TELEMETRY EXPLORER' : 'UPLOAD TELEMETRY'}</button></div>
    </section>
  </div>;
};

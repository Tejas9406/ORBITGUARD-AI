import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { KpiCard } from '../components/common/KpiCard';
import { SubsystemCard } from '../components/common/SubsystemCard';
import { AnomalyCard } from '../components/common/AnomalyCard';
import { GlassPanel } from '../components/common/GlassPanel';
import { SectionHeader } from '../components/common/SectionHeader';
import { TelemetryTimelineChart } from '../components/charts/TelemetryTimelineChart';
import { SatelliteGlobe } from '../components/space/SatelliteGlobe';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { useHealth } from '../hooks/useHealth';
import { useTelemetry } from '../hooks/useTelemetry';
import { useAnomalies } from '../hooks/useAnomalies';
import { SATELLITE_DIRECTORY } from '../data/satelliteDirectory';
import {
  HeartPulse,
  AlertTriangle,
  AlertOctagon,
  Radio,
  ArrowRight,
  Zap,
  Activity,
  Cpu,
  Layers,
  MapPin,
  Sparkles,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const querySatId = searchParams.get('satellite');
  const targetedSat = querySatId ? SATELLITE_DIRECTORY.find((s) => s.id === querySatId) : null;

  const { overallHealth, subsystems, isLoading: isHealthLoading, error: healthError } = useHealth();
  const { series, selectedChannel, isLoading: isTelemetryLoading, error: telemetryError } = useTelemetry('Channel_04');
  const { anomalies } = useAnomalies();

  if (isHealthLoading || isTelemetryLoading) {
    return <LoadingState message="Connecting to Satellite Telemetry Stream..." submessage="Initializing ISRO SPACE-03 mission telemetry and telemetry health models" />;
  }

  if (healthError || telemetryError) {
    return <ErrorState message={healthError || telemetryError || 'Failed to initialize mission telemetry'} />;
  }

  const pipelineStages = [
    { label: 'Telemetry Ingest', icon: Radio, status: 'NOMINAL', note: '1.0 Hz LEO Pass' },
    { label: 'AI Detection', icon: Cpu, status: 'ACTIVE', note: 'Isolation Forest + LSTM' },
    { label: 'Anomaly Scoring', icon: Activity, status: 'EVALUATED', note: 'Score: 0.94 CRITICAL' },
    { label: 'Attribution', icon: Layers, status: 'LOCALIZED', note: 'Top: Channel_04 (82%)' },
    { label: 'Subsystem', icon: MapPin, status: 'FLAGGED', note: 'EPS (Power Subsystem)' },
    { label: 'Health Update', icon: HeartPulse, status: 'DEGRADED', note: 'Score: 84/100 (-12)' },
    { label: 'Operator Alert', icon: AlertOctagon, status: 'TRIGGERED', note: 'Console Alert Active' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Satellite Health Dashboard"
        subtitle="Mission Control • Real-Time Telemetry Stream Ingestion, Multi-Channel Anomaly Attribution & Health Diagnostics."
        badge="ISRO SPACE-03 MISSION CONSOLE"
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/replay')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded bg-[#13233F] hover:bg-[#1A3056] text-cyan-300 border border-cyan-500/40 transition-colors shadow-sm"
            >
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              <span>LAUNCH REPLAY</span>
            </button>
            <button
              onClick={() => navigate('/anomalies')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded bg-rose-600 hover:bg-rose-500 text-white transition-colors shadow-sm"
            >
              <AlertOctagon className="w-3.5 h-3.5" />
              <span>REVIEW ALERTS (2)</span>
            </button>
          </div>
        }
      />

      {/* Primary KPI Section (4 Glass KPI Cards) */}
      <section aria-label="Key Performance Indicators" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Overall Health"
          value={overallHealth?.overallScore ?? 84}
          unit="/100"
          subtitle="Evaluation Score"
          statusText={overallHealth?.status ?? 'ATTENTION'}
          statusVariant="attention"
          icon={HeartPulse}
          trend="down"
          trendValue="-12 pts"
          tag="DEMO"
          onClick={() => navigate('/health')}
        />

        <KpiCard
          title="Active Anomalies"
          value={overallHealth?.activeAnomaliesCount ?? 2}
          subtitle="Subsystem Deviations"
          statusText="Needs Attention"
          statusVariant="attention"
          icon={AlertTriangle}
          trend="up"
          trendValue="+1 new"
          tag="DEMO"
          onClick={() => navigate('/anomalies')}
        />

        <KpiCard
          title="Critical Alerts"
          value={overallHealth?.criticalAlertsCount ?? 1}
          subtitle="Bus Voltage Sag"
          statusText="Immediate Review"
          statusVariant="critical"
          icon={AlertOctagon}
          tag="DEMO"
          onClick={() => navigate('/anomalies?id=ANM-0047')}
        />

        <KpiCard
          title="Channels Monitored"
          value={overallHealth?.monitoredChannelsCount ?? 82}
          subtitle="All Subsystem Vectors"
          statusText="100% Streamed"
          statusVariant="nominal"
          icon={Radio}
          tag="DEMO"
          onClick={() => navigate('/telemetry')}
        />
      </section>

      {/* Focused Satellite Target Banner (when redirected from 3D Earth) */}
      {targetedSat && (
        <div className="p-3.5 rounded bg-[#09152C]/90 border border-cyan-500/50 backdrop-blur-md flex items-center justify-between text-xs font-mono animate-fade-in shadow-[0_0_20px_rgba(0,229,255,0.18)]">
          <div className="flex flex-wrap items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span className="text-slate-400 font-semibold uppercase">FOCUSED ORBITAL TARGET:</span>
            <span className="text-white font-bold text-sm">{targetedSat.name}</span>
            <span className="text-slate-500">|</span>
            <span className="text-cyan-300">{targetedSat.orbitType} ({targetedSat.altitudeKm} km)</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-300">Ground Track: {targetedSat.currentSubpoint.geographicRegion}</span>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-slate-400 hover:text-cyan-300 text-[11px] underline cursor-pointer ml-4"
          >
            Clear Focus
          </button>
        </div>
      )}

      {/* Main Section: 3D Earth Orbit (Left 8 Cols) + Active Anomalies Queue (Right 4 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <section aria-label="3D Earth Orbit Visualization" className="lg:col-span-8 flex flex-col">
          <SatelliteGlobe
            selectedSatelliteId={targetedSat ? targetedSat.id : undefined}
            status={targetedSat ? targetedSat.status : 'CRITICAL'}
            healthScore={overallHealth?.overallScore ?? 84}
            activeAnomaliesCount={overallHealth?.activeAnomaliesCount ?? 2}
            height={440}
            onNavigateTelemetry={() => navigate('/telemetry')}
            onNavigateAnomaly={() => navigate('/anomalies?id=ANM-0047')}
          />
        </section>

        <section aria-label="Active Anomalies Queue" className="lg:col-span-4 flex flex-col">
          <GlassPanel cornerAccents={true} className="flex-1 flex flex-col justify-between">
            <div>
              <SectionHeader
                title="Active Anomaly Queue"
                subtitle="Flagged Subsystem Telemetry"
                icon={AlertOctagon}
                badge={`${anomalies.length} ACTIVE`}
                dotColor="red"
              />

              <div className="space-y-3 mt-3">
                {anomalies.slice(0, 3).map((anm) => (
                  <AnomalyCard
                    key={anm.id}
                    anomaly={anm}
                    onClick={() => navigate(`/anomalies?id=${anm.id}`)}
                    onInvestigate={() => navigate(`/anomalies?id=${anm.id}`)}
                  />
                ))}
              </div>
            </div>

            <button
              onClick={() => navigate('/anomalies')}
              className="w-full mt-4 py-2.5 text-xs font-mono font-bold rounded bg-[#101D36] hover:bg-[#182C4C] text-cyan-300 border border-[#1E355B] flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>INSPECT ALL ANOMALIES</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </GlassPanel>
        </section>
      </div>

      {/* Main Telemetry Visualization: Full-Width Plotly Timeline */}
      <section aria-label="Main Telemetry Health Timeline">
        <TelemetryTimelineChart
          series={series}
          channelId={selectedChannel?.id ?? 'Channel_04'}
          channelName={selectedChannel?.name ?? 'Solar Array Primary Bus Voltage'}
          unit={selectedChannel?.unit ?? 'V'}
          height={410}
        />
      </section>

      {/* Subsystem Health Cards Grid (EPS, TCS, AOCS, TT&C) */}
      <section aria-label="Subsystem Health Diagnostics" className="space-y-3">
        <div className="flex items-center justify-between">
          <SectionHeader
            title="Subsystem Health Assessment"
            subtitle="Multi-Channel Telemetry Aggregation Across Key Spacecraft Busses"
            icon={Zap}
            badge="4 BUSSES EVALUATED"
            dotColor="cyan"
            className="pb-0 mb-0 border-b-0"
          />
          <button
            onClick={() => navigate('/health')}
            className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
          >
            <span>Full Health Diagnostics</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {subsystems.map((sub) => (
            <SubsystemCard
              key={sub.id}
              subsystem={sub}
              onClick={() => navigate(`/health?subsystem=${sub.id}`)}
            />
          ))}
        </div>
      </section>

      {/* Mission Pipeline Flow & Ground Pipeline Status */}
      <section aria-label="SATSHIELD Detection Pipeline Flow">
        <GlassPanel cornerAccents={true} padding="md">
          <SectionHeader
            title="Real-Time SATSHIELD Telemetry Pipeline"
            subtitle="Core Architecture: DETECT → EXPLAIN → LOCALIZE → PRIORITIZE → ACT"
            icon={Sparkles}
            badge="AUTOMATED INFERENCE"
            dotColor="cyan"
          />

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mt-4">
            {pipelineStages.map((stage, idx) => {
              const Icon = stage.icon;
              const isAlert = stage.status === 'TRIGGERED' || stage.status === 'DEGRADED';
              return (
                <div
                  key={idx}
                  className={`p-3 rounded border text-center flex flex-col items-center justify-between text-xs font-mono transition-all ${
                    isAlert
                      ? 'bg-rose-950/40 border-rose-500/50 text-rose-300 shadow-[0_0_12px_rgba(239,68,68,0.2)]'
                      : 'bg-[#081122] border-[#162744] text-slate-300 hover:border-cyan-500/40'
                  }`}
                >
                  <div className={`p-1.5 rounded-full mb-1.5 ${isAlert ? 'bg-rose-900/60 text-rose-300' : 'bg-slate-800 text-cyan-400'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="font-bold text-[11px] uppercase tracking-tight">{stage.label}</span>
                  <span className={`text-[10px] mt-1 px-1.5 py-0.2 rounded font-semibold ${
                    isAlert ? 'bg-rose-900/70 text-rose-200' : 'bg-slate-800/80 text-cyan-300'
                  }`}>
                    {stage.status}
                  </span>
                  <span className="text-[9px] text-slate-400 mt-1">{stage.note}</span>
                </div>
              );
            })}
          </div>

          <div className="mt-4 pt-3 border-t border-[#182C4C]/60 flex flex-wrap items-center justify-between text-xs font-mono text-slate-400 gap-3">
            <div className="flex items-center gap-4">
              <span>Stream: <b className="text-emerald-400">ONLINE</b></span>
              <span>AI Engine: <b className="text-cyan-400">ISRO-SPACE03</b></span>
              <span>API Gateway: <b className="text-amber-400">FASTAPI READY (DEMO)</b></span>
            </div>
            <span>Ground Pass: #0924 • S-Band Tracking Active</span>
          </div>
        </GlassPanel>
      </section>
    </div>
  );
};

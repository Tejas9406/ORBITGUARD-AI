import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { GlassPanel } from '../components/common/GlassPanel';
import { SectionHeader } from '../components/common/SectionHeader';
import { AnomalyInspectionChart } from '../components/charts/AnomalyInspectionChart';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { useAnomalies } from '../hooks/useAnomalies';
import {
  AlertOctagon,
  Activity,
  Layers,
  HelpCircle,
  ShieldCheck,
  Zap,
  Cpu,
} from 'lucide-react';

export const AnomalyAnalysisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const anomalyParamId = searchParams.get('id') || undefined;

  const {
    anomalies,
    selectedAnomaly,
    selectedAnomalyId,
    setSelectedAnomalyId,
    severityFilter,
    setSeverityFilter,
    statusFilter,
    setStatusFilter,
    isLoading,
    error,
    reload,
  } = useAnomalies(anomalyParamId);

  useEffect(() => {
    if (anomalyParamId) {
      setSelectedAnomalyId(anomalyParamId);
    }
  }, [anomalyParamId, setSelectedAnomalyId]);

  if (isLoading) {
    return <LoadingState message="Fetching Anomaly Records..." submessage="Analyzing detection evidence from machine learning pipeline" />;
  }

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!selectedAnomaly) return <div className="sat-panel p-6"><h2 className="font-mono font-bold">No consensus events in the current run</h2><p className="mt-2 text-sm text-slate-400">Run analysis from Telemetry Explorer to produce event evidence. A run with zero events is valid and is not shown as an error.</p><button onClick={() => navigate('/telemetry')} className="mt-4 rounded bg-cyan-600 px-3 py-2 text-xs font-mono font-bold text-white">OPEN TELEMETRY EXPLORER</button></div>;

  // Derive target subsystem route
  const subsystemRouteId = selectedAnomaly.subsystem.toLowerCase().includes('power')
    ? 'power'
    : selectedAnomaly.subsystem.toLowerCase().includes('thermal')
    ? 'thermal'
    : selectedAnomaly.subsystem.toLowerCase().includes('attitude')
    ? 'aocs'
    : 'ttc';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Anomaly Analysis & Attribution"
        subtitle="Core product flow: DETECT → EXPLAIN → LOCALIZE → PRIORITIZE → ACT"
        badge="ISRO SPACE-03 INFERENCE"
        action={
          <button
            onClick={() => navigate('/replay')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded bg-[#101D36] hover:bg-[#182C4C] text-cyan-300 border border-cyan-500/40 transition-colors"
          >
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>REPLAY THIS EVENT IN SIMULATOR</span>
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (4 cols): Anomaly Events List & Filters */}
        <section aria-label="Anomaly Events Queue" className="lg:col-span-4 space-y-4">
          <GlassPanel cornerAccents={true}>
            <SectionHeader
              title={`Anomaly Events (${anomalies.length})`}
              subtitle="ISRO SPACE-03 DETECTIONS"
              icon={AlertOctagon}
              badge="DEMO DATA"
              dotColor="red"
            />

            {/* Filter controls */}
            <div className="grid grid-cols-2 gap-2 mb-3 mt-2">
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as any)}
                className="bg-[#070D1B] border border-[#16294A] rounded p-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-400"
                aria-label="Filter by Severity"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-[#070D1B] border border-[#16294A] rounded p-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-400"
                aria-label="Filter by Status"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INVESTIGATING">Investigating</option>
                <option value="MITIGATED">Mitigated</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>

            {/* Event rows */}
            <div className="space-y-2 max-h-[580px] overflow-y-auto pr-1">
              {anomalies.map((anm) => {
                const isSelected = anm.id === selectedAnomalyId;
                return (
                  <div
                    key={anm.id}
                    onClick={() => setSelectedAnomalyId(anm.id)}
                    role="button"
                    tabIndex={0}
                    className={`sat-glass-card p-3 transition-all duration-150 cursor-pointer ${
                      isSelected
                        ? 'bg-[#152545] border-cyan-400 shadow-[0_0_12px_rgba(0,229,255,0.25)]'
                        : 'hover:border-[#28406E] hover:bg-[#0E172B]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-mono font-bold text-slate-200">{anm.id}</span>
                      <SeverityBadge severity={anm.severity} size="sm" />
                    </div>

                    <p className="text-xs font-medium text-slate-300 line-clamp-1">{anm.title}</p>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#182C4C]/60 text-[11px] font-mono text-slate-400">
                      <span>{anm.channelId}</span>
                      <span>{anm.timestamp}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassPanel>
        </section>

        {/* Right Column (8 cols): Deep Anomaly Inspection */}
        <section aria-label="Anomaly Diagnostic Detail" className="lg:col-span-8 space-y-6">
          {/* Header Card for Selected Anomaly */}
          <GlassPanel cornerAccents={true} glow={selectedAnomaly.severity === 'CRITICAL' ? 'red' : 'amber'}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#1A2E50]/70 gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xl font-mono font-bold text-slate-100">{selectedAnomaly.id}</span>
                  <SeverityBadge severity={selectedAnomaly.severity} size="md" />
                  <StatusBadge status={selectedAnomaly.status} size="md" showPulse={selectedAnomaly.status === 'ACTIVE'} />
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/40">
                    {selectedAnomaly.subsystem}
                  </span>
                </div>
                <h3 className="text-sm md:text-base font-semibold text-slate-200 mt-1">
                  {selectedAnomaly.title}
                </h3>
              </div>

              <div className="text-left sm:text-right font-mono shrink-0">
                <span className="text-[10px] text-slate-400 uppercase block">Detection Timestamp</span>
                <span className="text-sm font-bold text-slate-200">{selectedAnomaly.timestamp}</span>
                <span className="text-[10px] text-slate-400 block mt-0.5">Epoch: 2026-10-09 UTC</span>
              </div>
            </div>

            {/* Value Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div className="p-2.5 rounded bg-[#070D1B] border border-[#16294A]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Observed Telemetry</span>
                <span className="text-lg font-mono font-bold text-rose-400">
                  {Number.isNaN(selectedAnomaly.observedValue) || selectedAnomaly.observedValue === 0 ? "N/A" : selectedAnomaly.observedValue} <span className="text-xs">{selectedAnomaly.unit}</span>
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#070D1B] border border-[#16294A]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Expected Baseline</span>
                <span className="text-lg font-mono font-bold text-slate-200">
                  {Number.isNaN(selectedAnomaly.expectedValue) ? "Multiple" : selectedAnomaly.expectedValue} <span className="text-xs font-normal text-slate-400">algorithms</span>
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#070D1B] border border-[#16294A]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Safety Limit</span>
                <span className="text-lg font-mono font-bold text-amber-400">
                  {Number.isNaN(selectedAnomaly.thresholdValue) ? "Consensus" : selectedAnomaly.thresholdValue} <span className="text-xs font-normal text-slate-400">derived</span>
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#070D1B] border border-[#16294A]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">ML Anomaly Score</span>
                <span className="text-lg font-mono font-bold text-cyan-300">
                  {selectedAnomaly.anomalyScore.toFixed(4)} <span className="text-xs font-normal text-slate-400">peak</span>
                </span>
              </div>
            </div>
          </GlassPanel>

          {/* Focused Anomaly Plotly Chart with Residuals */}
          <AnomalyInspectionChart anomaly={selectedAnomaly} height={350} />

          {/* SATSHIELD Differentiator: Glass AI Explanation Panel */}
          <GlassPanel cornerAccents={true} glow="cyan">
            <SectionHeader
              title="WHY WAS THIS FLAGGED? (AI Model Explainability)"
              subtitle="Telemetry deviation identified across multi-sensor correlation vector"
              icon={HelpCircle}
              badge="CONFIDENCE: HIGH (DEMO)"
              dotColor="cyan"
            />

            <p className="text-xs md:text-sm text-slate-200 leading-relaxed mb-4">
              {selectedAnomaly.explanation}
            </p>

            {/* Detection Evidence Cards */}
            <div className="space-y-2 mb-4">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold block">
                Quantitative Detection Evidence
              </span>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {selectedAnomaly.evidence.map((ev, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded bg-[#070D1B] border border-[#16294A] text-xs font-mono space-y-1"
                  >
                    <div className="flex items-center justify-between text-cyan-400 font-semibold">
                      <span>{ev.method}</span>
                      {ev.zScoreOrResidual !== undefined && (
                        <span className="text-rose-400">
                          {ev.zScoreOrResidual > 0 ? `+${ev.zScoreOrResidual}` : ev.zScoreOrResidual}σ
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 text-[11px] font-sans">{ev.confidenceNote}</p>
                    <div className="text-[10px] text-slate-400 pt-1 border-t border-[#13223E]">
                      Trigger: {ev.triggerCondition}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick cross-investigation buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-[#1A2E50]/70">
              <button
                onClick={() => navigate('/telemetry')}
                className="py-1.5 px-3 rounded bg-[#101D36] hover:bg-[#182C4C] text-cyan-300 text-xs font-mono font-bold border border-cyan-500/40 flex items-center gap-1.5 transition-colors"
              >
                <Activity className="w-3.5 h-3.5" />
                <span>VIEW TELEMETRY STREAM</span>
              </button>

              <button
                onClick={() => navigate(`/health?subsystem=${subsystemRouteId}`)}
                className="py-1.5 px-3 rounded bg-[#101D36] hover:bg-[#182C4C] text-amber-300 text-xs font-mono font-bold border border-amber-500/40 flex items-center gap-1.5 transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>VIEW SUBSYSTEM HEALTH ({selectedAnomaly.subsystem})</span>
              </button>

              <button
                onClick={() => navigate('/spacecraft')}
                className="py-1.5 px-3 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 text-xs font-mono font-bold border border-cyan-400/50 flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span>INSPECT IN 3D SPACECRAFT TWIN</span>
              </button>
            </div>
          </GlassPanel>

          {/* Contributing Channels (Ranking without fake percentages) */}
          <GlassPanel cornerAccents={true}>
            <SectionHeader
              title="Top Contributing Telemetry Channels (Channel Attribution)"
              subtitle="Telemetry channels ranked by contribution to multi-sensor divergence"
              icon={Layers}
              badge="RANKED ATTRIBUTION"
              dotColor="cyan"
            />

            <div className="space-y-2.5 mt-2">
              {selectedAnomaly.contributingChannels.map((cc) => (
                <div
                  key={cc.channelId}
                  className="flex items-center justify-between p-3 rounded bg-[#070D1B] border border-[#16294A] text-xs font-mono hover:border-cyan-500/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded bg-[#101D36] text-cyan-300 border border-[#1A2E50] flex items-center justify-center font-bold text-xs">
                      0{cc.rank}
                    </span>
                    <div>
                      <span className="font-bold text-slate-100">{cc.channelId}</span>
                      <span className="text-slate-400 ml-2 hidden sm:inline">{cc.name}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {cc.subsystem && (
                      <span className="text-slate-400 text-[11px] px-2 py-0.5 rounded bg-[#0A1224] border border-[#16294A]">
                        {cc.subsystem}
                      </span>
                    )}
                    {cc.deviationDelta && (
                      <span className="text-rose-400 font-bold bg-rose-950/60 px-2 py-0.5 rounded border border-rose-500/30">
                        {cc.deviationDelta}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>

          {/* Recommended Operational Action */}
          <GlassPanel glow="cyan" className="bg-gradient-to-r from-[#070D1B] to-[#0E1933] border-cyan-500/40">
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-mono text-xs font-bold text-cyan-300 uppercase tracking-wide">
                  Recommended Flight Controller Action
                </h4>
                <p className="text-xs text-slate-200 mt-1 leading-relaxed">
                  {selectedAnomaly.recommendedAction}
                </p>
              </div>
            </div>
          </GlassPanel>
        </section>
      </div>
    </div>
  );
};



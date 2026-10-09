import React from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/common/GlassPanel';
import { SectionHeader } from '../components/common/SectionHeader';
import { HealthGauge } from '../components/common/HealthGauge';
import { HealthCard } from '../components/common/HealthCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { SubsystemTrendChart } from '../components/charts/SubsystemTrendChart';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { useHealth } from '../hooks/useHealth';
import { Layers, ArrowRight } from 'lucide-react';

export const SubsystemHealthPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const querySubsystem = searchParams.get('subsystem');

  const {
    overallHealth,
    subsystems,
    selectedSubsystem,
    selectedSubsystemId,
    setSelectedSubsystemId,
    isLoading,
    error,
    reload,
  } = useHealth();

  useEffect(() => {
    if (querySubsystem) {
      setSelectedSubsystemId(querySubsystem);
    }
  }, [querySubsystem, setSelectedSubsystemId]);

  const handleSelectSubsystem = (id: string) => {
    setSelectedSubsystemId(id);
    setSearchParams({ subsystem: id });
  };

  if (isLoading) {
    return <LoadingState message="Evaluating Subsystem Health Models..." submessage="Synthesizing multi-channel telemetry vectors across EPS, TCS, AOCS, and TT&C" />;
  }

  if (error || !overallHealth) {
    return <ErrorState message={error || 'Failed to calculate health metrics'} onRetry={reload} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Satellite Subsystem Health"
        subtitle="Understand system and channel-level operational health degradation and recovery over time."
        badge="HEALTH ASSESSMENT"
      />

      {/* Top Banner: Overall Satellite Health Overview Gauge */}
      <GlassPanel variant="accent" cornerAccents className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          {/* Health Gauge Visual */}
          <div className="md:col-span-4 flex justify-center border-b md:border-b-0 md:border-r border-[#1E2D4A] pb-6 md:pb-0 md:pr-6">
            <HealthGauge
              score={overallHealth.overallScore}
              size={210}
              label="OVERALL HEALTH"
              sublabel="ISRO-SPACE03 Model Score"
            />
          </div>

          {/* Overall Health Description and Key Metrics */}
          <div className="md:col-span-8 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  Global Spacecraft Assessment
                </span>
                <h3 className="text-lg font-bold text-slate-100 font-mono flex items-center gap-2 mt-0.5">
                  Status: <StatusBadge status={overallHealth.status} size="md" showPulse />
                </h3>
              </div>
              <span className="text-xs font-mono text-cyan-400/80 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/20">
                Updated: {overallHealth.lastUpdated}
              </span>
            </div>

            <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
              Overall health is currently evaluated at <b className="text-amber-400 font-mono">84/100 (ATTENTION)</b> due to anomalous voltage sag in the Electrical Power System (EPS) primary bus and secondary battery thermal rise during pass #0924. AOCS and TT&C subsystems remain nominal.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="p-2.5 rounded bg-[#090F1C]/80 border border-[#182642] hover:border-rose-500/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Active Anomalies</span>
                <span className="text-base font-mono font-bold text-rose-400">
                  {overallHealth.activeAnomaliesCount} Active
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C]/80 border border-[#182642] hover:border-rose-500/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Critical Alerts</span>
                <span className="text-base font-mono font-bold text-rose-400">
                  {overallHealth.criticalAlertsCount} Critical
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C]/80 border border-[#182642] hover:border-cyan-500/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Channels Monitored</span>
                <span className="text-base font-mono font-bold text-slate-200">
                  {overallHealth.monitoredChannelsCount}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C]/80 border border-[#182642] hover:border-cyan-500/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Assessed Subsystems</span>
                <span className="text-base font-mono font-bold text-cyan-300">
                  {overallHealth.evaluatedSubsystems} / 4
                </span>
              </div>
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* Subsystem Health Cards Grid */}
      <section aria-label="Subsystem Breakdown" className="space-y-3">
        <SectionHeader
          title="SUBSYSTEM HEALTH STATUS"
          subtitle="Click subsystem card to focus diagnostics and health history"
          badge="4 FLIGHT BUSES"
          icon={Layers}
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {subsystems.map((sub) => (
            <HealthCard
              key={sub.id}
              subsystem={sub}
              isSelected={sub.id === selectedSubsystemId}
              onClick={() => handleSelectSubsystem(sub.id)}
            />
          ))}
        </div>
      </section>

      {/* Selected Subsystem Detail & Multi-Subsystem Plotly Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Selected Subsystem Detailed Card */}
        <GlassPanel variant="elevated" cornerAccents className="lg:col-span-5 p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A]/60">
            <div>
              <span className="font-mono text-xs text-cyan-400 font-semibold tracking-wider">
                DIAGNOSTICS: {selectedSubsystem.shortCode}
              </span>
              <h3 className="text-base font-bold text-slate-100 font-mono mt-0.5">
                {selectedSubsystem.name}
              </h3>
            </div>
            <StatusBadge status={selectedSubsystem.status} size="sm" showPulse={selectedSubsystem.status !== 'NOMINAL'} />
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded bg-[#090F1C]/80 border border-[#182642] flex items-center justify-between">
              <span className="text-slate-400">Health Index:</span>
              <span className={`text-lg font-bold ${
                selectedSubsystem.healthScore < 70 ? 'text-rose-400' : selectedSubsystem.healthScore < 85 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {selectedSubsystem.healthScore} / 100
              </span>
            </div>

            <div className="p-3 rounded bg-[#090F1C]/80 border border-[#182642] flex items-center justify-between">
              <span className="text-slate-400">Telemetry Health Trend:</span>
              <span className="text-amber-400 font-semibold">{selectedSubsystem.trend}</span>
            </div>

            <div className="p-3 rounded bg-[#090F1C]/80 border border-[#182642] flex items-center justify-between">
              <span className="text-slate-400">Primary Monitored Metric:</span>
              <span className="text-slate-200 font-semibold">{selectedSubsystem.primaryMetric.value}</span>
            </div>

            <div className="p-3 rounded bg-[#090F1C]/80 border border-[#182642] flex items-center justify-between">
              <span className="text-slate-400">Total Monitored Channels:</span>
              <span className="text-cyan-300 font-bold">{selectedSubsystem.totalChannelsMonitored} channels</span>
            </div>
          </div>

          {/* Key Channels mapped to this subsystem */}
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">
              Key Subsystem Telemetry Channels
            </span>
            <div className="flex flex-wrap gap-2">
              {selectedSubsystem.keyChannels.map((cId) => (
                <button
                  key={cId}
                  onClick={() => navigate(`/telemetry?channel=${cId}`)}
                  className="px-2.5 py-1 rounded bg-[#090F1C] hover:bg-[#15213B] text-xs font-mono text-cyan-300 border border-[#1E2D4A] hover:border-cyan-500/40 flex items-center gap-1.5 transition-all shadow-sm"
                  title={`Inspect ${cId} in Telemetry Explorer`}
                >
                  <span>{cId}</span>
                  <ArrowRight className="w-3 h-3 text-cyan-400" />
                </button>
              ))}
            </div>
          </div>

          {selectedSubsystem.activeAnomalyCount > 0 ? (
            <div className="p-3 rounded bg-rose-950/40 border border-rose-500/50 flex items-center justify-between text-xs font-mono">
              <span className="text-rose-300">Active Anomaly Detected</span>
              <button
                onClick={() => navigate('/anomalies')}
                className="text-rose-400 hover:text-rose-300 underline font-bold"
              >
                Inspect Event →
              </button>
            </div>
          ) : (
            <div className="p-2.5 rounded bg-emerald-950/30 border border-emerald-500/30 text-xs font-mono text-emerald-400 text-center">
              All monitored subsystem sensors operating nominally.
            </div>
          )}
        </GlassPanel>

        {/* Right Column (7 cols): Subsystem Trend Chart */}
        <section aria-label="Multi-Subsystem Health Trend" className="lg:col-span-7">
          <SubsystemTrendChart subsystems={subsystems} height={360} />
        </section>
      </div>
    </div>
  );
};

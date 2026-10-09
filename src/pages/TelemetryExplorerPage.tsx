import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { TelemetryTimelineChart } from '../components/charts/TelemetryTimelineChart';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { useTelemetry } from '../hooks/useTelemetry';
import {
  Search,
  RotateCcw,
  Layers,
  Sliders,
  Info,
} from 'lucide-react';

export const TelemetryExplorerPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const queryChannel = searchParams.get('channel');

  const {
    channels,
    selectedChannel,
    selectedChannelId,
    series,
    isLoading,
    error,
    selectChannel,
    reload,
  } = useTelemetry(queryChannel || 'Channel_04');

  useEffect(() => {
    if (queryChannel && queryChannel !== selectedChannelId) {
      selectChannel(queryChannel);
    }
  }, [queryChannel, selectedChannelId, selectChannel]);

  const [timeRange, setTimeRange] = useState<'1H' | '6H' | '24H' | '7D' | 'ALL'>('1H');
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [subsystemFilter, setSubsystemFilter] = useState('ALL');

  const filteredChannels = channels.filter((c) => {
    if (subsystemFilter !== 'ALL' && !c.subsystem.includes(subsystemFilter)) return false;
    if (anomalyOnly && c.status === 'NOMINAL') return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.id.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.subsystem.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleResetFilters = () => {
    setTimeRange('1H');
    setAnomalyOnly(false);
    setSearchQuery('');
    setSubsystemFilter('ALL');
  };

  if (isLoading) {
    return <LoadingState message="Loading Telemetry Channels..." submessage="Fetching satellite channel metrics from ISRO SPACE-03 stream" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Telemetry Explorer"
        subtitle="Inspect telemetry streams, compare baseline predictions, and investigate multi-channel anomalies."
        badge="TELEMETRY ANALYSIS"
      />

      {/* Filter and Control Bar */}
      <section aria-label="Telemetry Filters" className="sat-panel p-4 space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search bar */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by Channel ID, Name, or Subsystem..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#080E1C] border border-[#1E2D4A] rounded pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400"
            />
          </div>

          {/* Time range buttons */}
          <div className="flex items-center gap-1 bg-[#090E1A] p-1 rounded border border-[#1E2D4A] self-start md:self-auto">
            {(['1H', '6H', '24H', '7D', 'ALL'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-2.5 py-1 text-xs font-mono rounded transition-colors ${
                  timeRange === range
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-medium'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {range}
              </button>
            ))}
          </div>

          {/* Filter options */}
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={subsystemFilter}
              onChange={(e) => setSubsystemFilter(e.target.value)}
              className="bg-[#080E1C] border border-[#1E2D4A] text-xs font-mono text-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:border-cyan-400"
              aria-label="Filter by Subsystem"
            >
              <option value="ALL">All Subsystems</option>
              <option value="Power">Power (EPS)</option>
              <option value="Thermal">Thermal (TCS)</option>
              <option value="AOCS">Attitude (AOCS)</option>
              <option value="TT&C">Comms (TT&C)</option>
              <option value="Payload">Payload</option>
            </select>

            <label className="flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer bg-[#080E1C] px-2.5 py-1.5 rounded border border-[#1E2D4A]">
              <input
                type="checkbox"
                checked={anomalyOnly}
                onChange={(e) => setAnomalyOnly(e.target.checked)}
                className="rounded border-[#1E2D4A] text-cyan-500 focus:ring-0 bg-[#0F172A]"
              />
              <span>Anomalies Only</span>
            </label>

            <button
              onClick={handleResetFilters}
              className="px-2.5 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 transition-colors"
              title="Reset all filters"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          </div>
        </div>
      </section>

      {/* Main Grid: Channel List (Left) + Plotly Chart & Stats (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Channels Selector List */}
        <section aria-label="Available Channels" className="sat-panel p-4 flex flex-col max-h-[750px]">
          <div className="flex items-center justify-between pb-3 mb-2 border-b border-[#1E2D4A]/60">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <h3 className="font-mono text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Telemetry Channels ({filteredChannels.length})
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">SELECT TO PLOT</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredChannels.length === 0 ? (
              <div className="p-6 text-center text-xs font-mono text-slate-400">
                No telemetry channels match current filters.
              </div>
            ) : (
              filteredChannels.map((chan) => {
                const isSelected = chan.id === selectedChannelId;
                return (
                  <div
                    key={chan.id}
                    onClick={() => selectChannel(chan.id)}
                    role="button"
                    tabIndex={0}
                    className={`p-3 rounded border transition-all duration-150 cursor-pointer ${
                      isSelected
                        ? 'bg-[#152442] border-cyan-400 shadow-[0_0_12px_rgba(0,229,255,0.2)]'
                        : 'bg-[#0B1222] border-[#1A2844] hover:border-[#2D4573] hover:bg-[#0F182E]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-mono font-bold text-cyan-300">{chan.id}</span>
                      <StatusBadge status={chan.status} size="sm" />
                    </div>

                    <h4 className="text-xs font-medium text-slate-200 line-clamp-1">{chan.name}</h4>
                    <span className="text-[10px] font-mono text-slate-400">{chan.subsystem}</span>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#1E2D4A]/50 text-xs font-mono">
                      <span className="text-slate-400">Value:</span>
                      <span className="font-bold text-slate-100">
                        {chan.currentValue} {chan.unit}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* Right 2 Columns: Large Plotly Chart + Channel Metrics */}
        <section aria-label="Channel Visualization and Details" className="lg:col-span-2 space-y-6">
          <TelemetryTimelineChart
            series={series}
            channelId={selectedChannel.id}
            channelName={selectedChannel.name}
            unit={selectedChannel.unit}
            height={420}
          />

          {/* Statistical and Anomaly Summary Cards */}
          <div className="sat-panel p-5">
            <h3 className="font-mono text-xs font-semibold text-slate-200 uppercase tracking-wider pb-3 mb-4 border-b border-[#1E2D4A]/60 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                Channel Statistical Diagnostics ({selectedChannel.id})
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                Verified Telemetry Parameters
              </span>
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
              <div className="p-2.5 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Current</span>
                <span className="text-base font-mono font-bold text-slate-100">
                  {selectedChannel.currentValue} <span className="text-xs">{selectedChannel.unit}</span>
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Rolling Mean</span>
                <span className="text-base font-mono font-bold text-cyan-300">
                  {selectedChannel.mean} <span className="text-xs">{selectedChannel.unit}</span>
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Std Dev (σ)</span>
                <span className="text-base font-mono font-bold text-slate-200">
                  ±{selectedChannel.stdDev}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Min / Max</span>
                <span className="text-xs font-mono font-medium text-slate-300 block mt-1">
                  {selectedChannel.min} - {selectedChannel.max}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Anomaly Score</span>
                <span
                  className={`text-base font-mono font-bold ${
                    selectedChannel.anomalyScore > 0.7
                      ? 'text-rose-400'
                      : selectedChannel.anomalyScore > 0.4
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {selectedChannel.anomalyScore}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Active Anomalies</span>
                <span className="text-base font-mono font-bold text-rose-400">
                  {selectedChannel.recentAnomalyCount}
                </span>
              </div>
            </div>

            <div className="mt-4 p-3 rounded bg-[#0A1224] border border-[#1E2D4A] text-xs font-mono text-slate-400 flex items-start gap-2">
              <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>
                <b>Channel Spec:</b> {selectedChannel.description} Normal baseline envelope calculated using a 30-day rolling solar phase profile.
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

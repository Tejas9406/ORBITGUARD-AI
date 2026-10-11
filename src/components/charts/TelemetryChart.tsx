import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlotlyChartWrapper } from './PlotlyChartWrapper';
import { GlassPanel } from '../common/GlassPanel';
import { SectionHeader } from '../common/SectionHeader';
import type { TelemetryPoint } from '../../types/telemetry';
import { tokens } from '../../styles/tokens';
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  SlidersHorizontal,
  X,
  Clock,
} from 'lucide-react';

export type TimeRangeFilter = '5m' | '15m' | '30m' | '1h' | '6h' | '24h';

export interface TelemetryChartProps {
  series: TelemetryPoint[];
  channelId?: string;
  channelName: string;
  unit: string;
  height?: number;
  className?: string;
  onAnomalySelect?: (anomalyId: string) => void;
}

export const TelemetryChart: React.FC<TelemetryChartProps> = ({
  series,
  channelId = 'Channel_04',
  channelName,
  unit,
  height = 420,
  className = '',
  onAnomalySelect,
}) => {
  const navigate = useNavigate();

  // Trace visibility toggles
  const [showActual, setShowActual] = useState(true);
  const [showBaseline, setShowBaseline] = useState(true);
  const [showBounds, setShowBounds] = useState(true);
  const [showAnomalies, setShowAnomalies] = useState(true);

  // Time range selection
  const [timeRange, setTimeRange] = useState<TimeRangeFilter>('1h');

  // Selected anomaly inspection popup
  const [clickedAnomaly, setClickedAnomaly] = useState<{
    timestamp: string;
    value: number;
    baseline: number;
    score: number;
    anomalyId: string;
  } | null>(null);

  // Filter series based on selected time range
  const filteredSeries = useMemo(() => {
    if (!series || series.length === 0) return [];
    const total = series.length;
    switch (timeRange) {
      case '5m':
        return series.slice(Math.max(0, total - 10));
      case '15m':
        return series.slice(Math.max(0, total - 20));
      case '30m':
        return series.slice(Math.max(0, total - 35));
      case '1h':
        return series; // full 60 points window
      case '6h':
      case '24h':
      default:
        return series;
    }
  }, [series, timeRange]);

  const xTimestamps = filteredSeries.map((p) => p.timestamp);
  const yActual = filteredSeries.map((p) => p.value);
  const yBaseline = filteredSeries.map((p) => p.baseline ?? p.value);
  const yUpper = filteredSeries.map((p) => p.upperThreshold ?? null);
  const yLower = filteredSeries.map((p) => p.lowerThreshold ?? null);

  // Anomaly data points
  const anomalyPoints = filteredSeries.filter((p) => p.isAnomaly);
  const anomalyX = anomalyPoints.map((p) => p.timestamp);
  const anomalyY = anomalyPoints.map((p) => p.value);

  // Custom data arrays for rich technical hover diagnostics
  const actualCustomData = filteredSeries.map((p) => {
    const baseline = p.baseline ?? p.value;
    const delta = p.value - baseline;
    const deltaStr = delta >= 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2);
    return [
      p.timestamp,
      channelId,
      unit,
      baseline,
      deltaStr,
      p.anomalyScore ?? 0.04,
      p.isAnomaly ? 'CRITICAL DEVIATION' : 'NOMINAL',
    ];
  });

  const traces: any[] = [];

  // 1. Actual Telemetry Line (strongest cyan/blue line)
  if (showActual) {
    traces.push({
      x: xTimestamps,
      y: yActual,
      type: 'scatter',
      mode: 'lines+markers',
      name: `Actual Telemetry`,
      line: {
        color: tokens.chartTheme.telemetryLine,
        width: 2.5,
      },
      marker: {
        size: 4,
        color: tokens.chartTheme.telemetryLine,
      },
      customdata: actualCustomData,
      hovertemplate:
        `<b>%{customdata[0]}</b> • %{customdata[1]}<br>` +
        `Observed: <b>%{y:.2f} %{customdata[2]}</b><br>` +
        `Expected: %{customdata[3]:.2f} %{customdata[2]}<br>` +
        `Deviation: %{customdata[4]} %{customdata[2]}<br>` +
        `Score: <b>%{customdata[5]:.2f}</b><br>` +
        `Status: %{customdata[6]}<extra></extra>`,
    });
  }

  // 2. Expected Baseline (subtle dashed reference line)
  if (showBaseline) {
    traces.push({
      x: xTimestamps,
      y: yBaseline,
      type: 'scatter',
      mode: 'lines',
      name: 'Expected Baseline',
      line: {
        color: '#64748B',
        width: 1.8,
        dash: 'dash',
      },
      hovertemplate: `Expected Baseline: %{y:.2f} ${unit}<extra></extra>`,
    });
  }

  // 3. Operational Bounds (subtle dotted lines)
  if (showBounds) {
    traces.push(
      {
        x: xTimestamps,
        y: yUpper,
        type: 'scatter',
        mode: 'lines',
        name: 'Upper Operational Bound',
        line: {
          color: 'rgba(245, 158, 11, 0.75)',
          width: 1.2,
          dash: 'dot',
        },
        hovertemplate: `Upper Bound: %{y:.2f} ${unit}<extra></extra>`,
      },
      {
        x: xTimestamps,
        y: yLower,
        type: 'scatter',
        mode: 'lines',
        name: 'Lower Operational Bound',
        line: {
          color: 'rgba(245, 158, 11, 0.75)',
          width: 1.2,
          dash: 'dot',
        },
        hovertemplate: `Lower Bound: %{y:.2f} ${unit}<extra></extra>`,
      }
    );
  }

  // 4. Detected Anomaly Event Markers
  if (showAnomalies && anomalyPoints.length > 0) {
    const anomalyCustomData = anomalyPoints.map((p) => {
      const baseline = p.baseline ?? p.value;
      const delta = (p.value - baseline).toFixed(2);
      return [p.timestamp, p.anomalyScore ?? 0.94, delta, 'ANM-0047'];
    });

    traces.push({
      x: anomalyX,
      y: anomalyY,
      type: 'scatter',
      mode: 'markers',
      name: 'Anomaly Event',
      marker: {
        symbol: 'diamond',
        size: 11,
        color: tokens.chartTheme.anomalyMarker,
        line: {
          color: '#FFFFFF',
          width: 1.5,
        },
      },
      customdata: anomalyCustomData,
      hovertemplate:
        `<b>ANOMALY EVENT FLAGGED</b><br>` +
        `Time: %{x}<br>` +
        `Observed: <b>%{y:.2f} ${unit}</b><br>` +
        `Score: <b>%{customdata[1]:.2f}</b><br>` +
        `Residual: %{customdata[2]} ${unit}<br>` +
        `Event: %{customdata[3]}<br>` +
        `<i>Click marker to inspect root cause</i><extra></extra>`,
    });
  }

  // 5. Highlighted Anomaly Region (transparent red/amber glass-like overlay)
  const shapes: any[] = [];
  if (showAnomalies && anomalyPoints.length > 0) {
    const firstAnomaly = anomalyPoints[0].timestamp;
    const lastAnomaly = anomalyPoints[anomalyPoints.length - 1].timestamp;
    shapes.push({
      type: 'rect',
      xref: 'x',
      yref: 'paper',
      x0: firstAnomaly,
      x1: lastAnomaly,
      y0: 0,
      y1: 1,
      fillcolor: 'rgba(239, 68, 68, 0.12)',
      line: {
        color: 'rgba(239, 68, 68, 0.45)',
        width: 1,
        dash: 'dot',
      },
    });
  }

  // Plotly dark aerospace layout configuration
  const layout: Partial<Plotly.Layout> = {
    title: {
      text: `${channelId} Telemetry Stream — ${channelName}`,
      font: { color: '#E2E8F0', size: 12, family: 'JetBrains Mono' },
      x: 0.02,
      y: 0.98,
    },
    shapes,
    margin: { l: 52, r: 24, t: 45, b: 38 },
    yaxis: {
      title: { text: unit, font: { color: '#94A3B8', size: 11 } },
      gridcolor: '#13213A',
      zerolinecolor: '#1D3256',
      tickfont: { color: '#94A3B8', size: 10, family: 'JetBrains Mono' },
    },
    xaxis: {
      gridcolor: '#13213A',
      zerolinecolor: '#1D3256',
      tickfont: { color: '#94A3B8', size: 10, family: 'JetBrains Mono' },
      nticks: 8,
    },
    legend: {
      orientation: 'h',
      x: 0,
      y: 1.14,
      font: { size: 10, color: '#CBD5E1', family: 'Inter' },
      bgcolor: 'transparent',
    },
  };

  // Handle clicking anomaly point on chart
  const handleChartClick = (event: any) => {
    if (!event || !event.points || event.points.length === 0) return;
    const pt = event.points[0];

    // Check if clicked point is in the anomaly markers trace or an anomalous point
    if (pt.data && pt.data.name === 'Anomaly Event') {
      const custom = pt.customdata || [];
      const anmId = custom[3] || 'ANM-0047';
      setClickedAnomaly({
        timestamp: pt.x,
        value: pt.y,
        baseline: pt.y - parseFloat(custom[2] || '0'),
        score: custom[1] || 0.94,
        anomalyId: anmId,
      });
      if (onAnomalySelect) onAnomalySelect(anmId);
    } else {
      // If clicking an actual point that is an anomaly
      const matched = filteredSeries.find((p) => p.timestamp === pt.x && p.isAnomaly);
      if (matched) {
        setClickedAnomaly({
          timestamp: matched.timestamp,
          value: matched.value,
          baseline: matched.baseline ?? matched.value,
          score: matched.anomalyScore ?? 0.94,
          anomalyId: 'ANM-0047',
        });
      }
    }
  };

  const handleInvestigate = (anomalyId: string) => {
    navigate(`/anomalies?id=${anomalyId}`);
  };

  return (
    <GlassPanel cornerAccents={true} padding="none" className={`flex flex-col ${className}`}>
      {/* Top Header & Diagnostics Toolbar */}
      <div className="p-4 border-b border-[#1A2E50]/70 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <SectionHeader
            title="Telemetry Health Timeline"
            subtitle={`${channelId}: ${channelName} • Buffer 60s @ 1Hz (SIMULATED)`}
            icon={Activity}
            badge="ISRO-SPACE03 STREAM"
            dotColor="cyan"
            className="pb-0 mb-0 border-b-0"
          />

          {/* Time range selection controls */}
          <div className="flex items-center gap-1 bg-[#070D1B]/80 p-1 rounded border border-[#16294A] self-start sm:self-auto">
            <span className="text-[10px] font-mono text-slate-400 px-1.5 flex items-center gap-1">
              <Clock className="w-3 h-3 text-cyan-400" />
              WINDOW:
            </span>
            {(['5m', '15m', '30m', '1h', '6h', '24h'] as TimeRangeFilter[]).map((tr) => (
              <button
                key={tr}
                onClick={() => setTimeRange(tr)}
                className={`px-2 py-0.5 text-[11px] font-mono rounded transition-colors ${
                  timeRange === tr
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title={`Set time window to ${tr}`}
              >
                {tr}
              </button>
            ))}
          </div>
        </div>

        {/* Trace Active Toggle Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#16294A]/60 text-xs font-mono">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1 mr-1">
              <SlidersHorizontal className="w-3 h-3 text-cyan-400" />
              TRACES:
            </span>

            {/* ACTUAL TOGGLE */}
            <button
              onClick={() => setShowActual((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all border ${
                showActual
                  ? 'bg-cyan-950/70 text-cyan-300 border-cyan-400/60 shadow-[0_0_8px_rgba(0,229,255,0.2)] font-bold'
                  : 'bg-slate-900/60 text-slate-500 border-slate-800'
              }`}
            >
              [ ACTUAL ]
            </button>

            {/* BASELINE TOGGLE */}
            <button
              onClick={() => setShowBaseline((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all border ${
                showBaseline
                  ? 'bg-slate-800/80 text-slate-200 border-slate-600 font-medium'
                  : 'bg-slate-900/60 text-slate-500 border-slate-800'
              }`}
            >
              [ BASELINE ]
            </button>

            {/* BOUNDS TOGGLE */}
            <button
              onClick={() => setShowBounds((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all border ${
                showBounds
                  ? 'bg-amber-950/60 text-amber-300 border-amber-500/50 font-medium'
                  : 'bg-slate-900/60 text-slate-500 border-slate-800'
              }`}
            >
              [ BOUNDS ]
            </button>

            {/* ANOMALIES TOGGLE */}
            <button
              onClick={() => setShowAnomalies((prev) => !prev)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all border ${
                showAnomalies
                  ? 'bg-rose-950/70 text-rose-300 border-rose-500/60 shadow-[0_0_8px_rgba(239,68,68,0.2)] font-bold'
                  : 'bg-slate-900/60 text-slate-500 border-slate-800'
              }`}
            >
              [ ANOMALIES ({series.filter((p) => p.isAnomaly).length}) ]
            </button>
          </div>

          <div className="flex items-center gap-2 text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              CADENCE: 1.0Hz
            </span>
            <span className="text-slate-600">•</span>
            <span className="text-cyan-400">DOUBLE CLICK: RESET ZOOM</span>
          </div>
        </div>
      </div>

      {/* Main Interactive Plotly Area */}
      <div className="p-2 relative" style={{ height }}>
        <PlotlyChartWrapper
          data={traces}
          layout={layout}
          onClick={handleChartClick}
        />

        {/* Floating Glass Anomaly Inspection Card triggered upon marker click */}
        {clickedAnomaly && (
          <div className="absolute top-4 right-4 z-20 w-80 sat-glass-card border-rose-500/50 bg-[#0A1224]/95 p-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-rose-400" />
                <span className="font-mono text-xs font-bold text-rose-300">
                  {clickedAnomaly.anomalyId} INSPECTION
                </span>
              </div>
              <button
                onClick={() => setClickedAnomaly(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                aria-label="Close inspection popup"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-slate-100">{clickedAnomaly.timestamp}</span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Observed Value:</span>
                <span className="text-rose-400 font-bold">{clickedAnomaly.value.toFixed(2)} {unit}</span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Expected Baseline:</span>
                <span>{clickedAnomaly.baseline.toFixed(2)} {unit}</span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Anomaly Score:</span>
                <span className="text-rose-400 font-bold">{clickedAnomaly.score}</span>
              </div>
            </div>

            <button
              onClick={() => handleInvestigate(clickedAnomaly.anomalyId)}
              className="mt-3 w-full py-1.5 px-3 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-bold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              <span>INVESTIGATE IN ANOMALY ANALYZER</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </GlassPanel>
  );
};

export default TelemetryChart;

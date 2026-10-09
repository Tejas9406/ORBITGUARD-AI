import { PlotlyChartWrapper } from './PlotlyChartWrapper';
import type { AnomalyEvent } from '../../types/anomaly';
import { generateDemoTelemetrySeries } from '../../data/demoTelemetry';

interface AnomalyInspectionChartProps {
  anomaly: AnomalyEvent;
  height?: number;
}

export const AnomalyInspectionChart: React.FC<AnomalyInspectionChartProps> = ({
  anomaly,
  height = 360,
}) => {
  const series = generateDemoTelemetrySeries(anomaly.channelId);

  // Focus specifically on the anomaly window (+/- 12 minutes around event)
  const windowIndex = series.findIndex((p) => p.isAnomaly);
  const startIdx = Math.max(0, (windowIndex !== -1 ? windowIndex : 36) - 10);
  const endIdx = Math.min(series.length, startIdx + 24);
  const windowSlice = series.slice(startIdx, endIdx);

  const xTimestamps = windowSlice.map((p) => p.timestamp);
  const yObserved = windowSlice.map((p) => p.value);
  const yExpected = windowSlice.map((p) => p.baseline ?? p.value);
  const residuals = windowSlice.map((p) => parseFloat(Math.abs(p.value - (p.baseline ?? p.value)).toFixed(2)));

  const traces: any[] = [
    {
      x: xTimestamps,
      y: yObserved,
      type: 'scatter',
      mode: 'lines+markers',
      name: `Observed (${anomaly.unit})`,
      line: { color: '#00E5FF', width: 2.5 },
      marker: { size: 5, color: '#00E5FF' },
      hovertemplate: `Observed: %{y:.2f} ${anomaly.unit}<extra></extra>`,
    },
    {
      x: xTimestamps,
      y: yExpected,
      type: 'scatter',
      mode: 'lines',
      name: 'Expected Baseline',
      line: { color: '#94A3B8', width: 2, dash: 'dash' },
      hovertemplate: `Expected: %{y:.2f} ${anomaly.unit}<extra></extra>`,
    },
    {
      x: xTimestamps,
      y: residuals,
      type: 'bar',
      name: 'Model Residual (|Δ|)',
      yaxis: 'y2',
      marker: {
        color: windowSlice.map((p) =>
          p.isAnomaly ? 'rgba(239, 68, 68, 0.7)' : 'rgba(168, 85, 247, 0.4)'
        ),
      },
      hovertemplate: `Residual Delta: %{y:.2f} ${anomaly.unit}<extra></extra>`,
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    title: {
      text: `Anomaly Root Cause Window: ${anomaly.id} — ${anomaly.channelName}`,
      font: { color: '#F1F5F9', size: 13, family: 'JetBrains Mono' },
      x: 0.02,
      y: 0.98,
    },
    grid: { rows: 2, columns: 1, pattern: 'independent' },
    yaxis: {
      domain: [0.35, 1],
      title: { text: anomaly.unit, font: { color: '#94A3B8', size: 10 } },
      gridcolor: '#182642',
      tickfont: { color: '#94A3B8', size: 10 },
    },
    yaxis2: {
      domain: [0, 0.28],
      title: { text: '|Δ| Residual', font: { color: '#A855F7', size: 10 } },
      gridcolor: '#182642',
      tickfont: { color: '#94A3B8', size: 9 },
    },
    xaxis: {
      gridcolor: '#182642',
      tickfont: { color: '#94A3B8', size: 10 },
    },
    margin: { l: 50, r: 25, t: 45, b: 35 },
    legend: {
      orientation: 'h',
      x: 0,
      y: 1.12,
      font: { size: 10, color: '#CBD5E1' },
      bgcolor: 'transparent',
    },
  };

  return (
    <div className="sat-panel p-4 flex flex-col">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#1E2D4A]/60">
        <span className="font-mono text-xs font-semibold text-rose-400 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
          ANOMALY WINDOW RESOLUTION: {anomaly.timestamp}
        </span>
        <span className="text-[11px] font-mono text-slate-400">
          Detection: {anomaly.detectionMethod}
        </span>
      </div>
      <div style={{ height }}>
        <PlotlyChartWrapper data={traces} layout={layout} />
      </div>
    </div>
  );
};

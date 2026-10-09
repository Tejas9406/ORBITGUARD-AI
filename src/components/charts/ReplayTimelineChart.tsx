import { PlotlyChartWrapper } from './PlotlyChartWrapper';
import type { ReplayFrame } from '../../types/mission';

interface ReplayTimelineChartProps {
  framesHistory: ReplayFrame[];
  currentFrame: ReplayFrame;
  height?: number;
}

export const ReplayTimelineChart: React.FC<ReplayTimelineChartProps> = ({
  framesHistory,
  currentFrame,
  height = 360,
}) => {
  const xMissionTime = framesHistory.map((f) => f.missionTime);
  const yVoltage = framesHistory.map((f) => f.solarArrayVoltage);
  const yScore = framesHistory.map((f) => f.anomalyScore * 30); // Normalized scale for comparison
  const anomalyPoints = framesHistory.filter((f) => f.hasActiveAnomaly);

  const traces: any[] = [
    {
      x: xMissionTime,
      y: yVoltage,
      type: 'scatter',
      mode: 'lines+markers',
      name: 'Channel_04 Voltage (V)',
      line: { color: '#00E5FF', width: 2.5 },
      marker: { size: 4, color: '#00E5FF' },
      hovertemplate: `Time: %{x}<br>Voltage: %{y:.2f} V<extra></extra>`,
    },
    {
      x: xMissionTime,
      y: yScore,
      type: 'scatter',
      mode: 'lines',
      name: 'AI Anomaly Score (×30)',
      line: { color: '#F59E0B', width: 1.8, dash: 'dot' },
      hovertemplate: `Score Factor: %{y:.2f}<extra></extra>`,
    },
  ];

  if (anomalyPoints.length > 0) {
    traces.push({
      x: anomalyPoints.map((f) => f.missionTime),
      y: anomalyPoints.map((f) => f.solarArrayVoltage),
      type: 'scatter',
      mode: 'markers',
      name: 'Active Anomaly Detected',
      marker: {
        symbol: 'diamond',
        size: 10,
        color: '#EF4444',
        line: { color: '#FFFFFF', width: 1.5 },
      },
      hovertemplate: `<b>ANOMALY TRIGGERED</b><br>Time: %{x}<br>Voltage: %{y:.2f} V<extra></extra>`,
    });
  }

  const layout: Partial<Plotly.Layout> = {
    title: {
      text: `Replay Telemetry Progression — Synchronized at ${currentFrame.missionTime}`,
      font: { color: '#F1F5F9', size: 12, family: 'JetBrains Mono' },
      x: 0.02,
      y: 0.98,
    },
    yaxis: {
      title: { text: 'Telemetry (V) / Score', font: { color: '#94A3B8', size: 10 } },
      range: [20, 32],
      gridcolor: '#182642',
      tickfont: { color: '#94A3B8', size: 10 },
    },
    xaxis: {
      gridcolor: '#182642',
      tickfont: { color: '#94A3B8', size: 10 },
    },
    margin: { l: 50, r: 25, t: 40, b: 35 },
    legend: {
      orientation: 'h',
      x: 0,
      y: 1.15,
      font: { size: 10, color: '#CBD5E1' },
      bgcolor: 'transparent',
    },
  };

  return (
    <div className="sat-panel p-4 flex flex-col">
      <div style={{ height }}>
        <PlotlyChartWrapper data={traces} layout={layout} />
      </div>
    </div>
  );
};

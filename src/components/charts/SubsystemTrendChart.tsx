import { PlotlyChartWrapper } from './PlotlyChartWrapper';
import type { SubsystemHealth } from '../../types/health';

interface SubsystemTrendChartProps {
  subsystems: SubsystemHealth[];
  height?: number;
}

export const SubsystemTrendChart: React.FC<SubsystemTrendChartProps> = ({
  subsystems,
  height = 300,
}) => {
  const colors: Record<string, string> = {
    power: '#EF4444', // Red (degraded)
    thermal: '#F59E0B', // Amber (warning)
    aocs: '#00E5FF', // Cyan (nominal)
    ttc: '#10B981', // Green (nominal)
  };

  const traces: any[] = subsystems.map((sub) => {
    return {
      x: sub.historicalScores.map((h) => h.time),
      y: sub.historicalScores.map((h) => h.score),
      type: 'scatter',
      mode: 'lines+markers',
      name: `${sub.shortCode} (${sub.healthScore}/100)`,
      line: {
        color: colors[sub.id] || '#38BDF8',
        width: 2.2,
      },
      marker: {
        size: 5,
        color: colors[sub.id] || '#38BDF8',
      },
      hovertemplate: `<b>${sub.name}</b><br>Time: %{x}<br>Health: %{y}/100<extra></extra>`,
    };
  });

  const layout: Partial<Plotly.Layout> = {
    title: {
      text: 'Subsystem Health Evaluation Trend (Past 45 mins)',
      font: { color: '#F1F5F9', size: 12, family: 'JetBrains Mono' },
      x: 0.02,
      y: 0.98,
    },
    yaxis: {
      title: { text: 'Health Score (0-100)', font: { color: '#94A3B8', size: 10 } },
      range: [50, 105],
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

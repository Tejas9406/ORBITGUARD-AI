import { PlotlyChartWrapper } from './PlotlyChartWrapper';
import type { AnomalyEvent } from '../../types/anomaly';
interface Props { anomaly: AnomalyEvent; height?: number }
/** Event detail deliberately renders only evidence returned for that exact event. */
export const AnomalyInspectionChart: React.FC<Props> = ({ anomaly, height = 360 }) => {
  const traces: any[] = [{ x: [anomaly.timestamp], y: [anomaly.observedValue], type: 'scatter', mode: 'markers', name: 'Observed event evidence', marker: { size: 12, color: '#fb7185' }, hovertemplate: `Observed: %{y} ${anomaly.unit}<extra></extra>` }];
  const layout: Partial<Plotly.Layout> = { title: { text: `Event evidence: ${anomaly.id}`, font: { color: '#F1F5F9', size: 13 }, x: .02 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', xaxis: { title: { text: 'Event timestamp', font: { color: '#94A3B8' } }, tickfont: { color: '#94A3B8' }, gridcolor: '#182642' }, yaxis: { title: { text: anomaly.unit, font: { color: '#94A3B8' } }, tickfont: { color: '#94A3B8' }, gridcolor: '#182642' }, margin: { l: 50, r: 25, t: 45, b: 35 } };
  return <div className="sat-panel p-4"><p className="mb-2 text-xs font-mono text-slate-400">This marker is the recorded value for the selected consensus event. Inspect the Telemetry Explorer for the complete source timeline.</p><div style={{ height }}><PlotlyChartWrapper data={traces} layout={layout} /></div></div>;
};

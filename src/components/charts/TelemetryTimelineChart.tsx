import { TelemetryChart } from './TelemetryChart';
import type { TelemetryPoint } from '../../types/telemetry';

export interface TelemetryTimelineChartProps {
  series: TelemetryPoint[];
  channelId?: string;
  channelName: string;
  unit: string;
  height?: number;
  onAnomalySelect?: (anomalyId: string) => void;
}

export function TelemetryTimelineChart(props: TelemetryTimelineChartProps) {
  return <TelemetryChart {...props} />;
}

export default TelemetryTimelineChart;

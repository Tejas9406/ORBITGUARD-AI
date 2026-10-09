import { AlertOctagon, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface AlertBannerProps {
  anomalyId?: string;
  channelName?: string;
  severity?: 'CRITICAL' | 'HIGH';
  message: string;
  onInvestigate?: () => void;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({
  anomalyId = 'ANM-0047',
  channelName = 'Channel_04 (Solar Array Bus Voltage)',
  severity = 'CRITICAL',
  message,
  onInvestigate,
}) => {
  return (
    <div
      role="alert"
      className="bg-rose-950/45 backdrop-blur-md border-y md:border border-rose-500/60 p-3 md:px-4 md:py-2.5 md:rounded-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-[0_0_20px_-3px_rgba(239,68,68,0.3)]"
    >
      <div className="flex items-center gap-3">
        <div className="p-1.5 rounded bg-rose-900/60 text-rose-300 border border-rose-500/50 shrink-0">
          <AlertOctagon className="w-5 h-5 text-rose-400 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-rose-600 text-white tracking-wider">
              {severity} TELEMETRY ANOMALY
            </span>
            <span className="font-mono text-xs text-rose-200 font-semibold">{anomalyId}</span>
            <span className="text-xs text-slate-400 hidden sm:inline">•</span>
            <span className="text-xs font-mono text-cyan-300">{channelName}</span>
          </div>
          <p className="text-xs text-rose-200/90 mt-0.5">{message}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 self-end md:self-auto shrink-0">
        <Link
          to={`/anomalies?id=${anomalyId}`}
          onClick={onInvestigate}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-semibold rounded bg-rose-600 hover:bg-rose-500 text-white transition-colors focus:ring-2 focus:ring-rose-400 focus:outline-none"
        >
          <span>INVESTIGATE ROOT CAUSE</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
};

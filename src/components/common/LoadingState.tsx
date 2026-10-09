import { Radio } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  submessage?: string;
  heightClass?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Acquiring Telemetry Stream...',
  submessage = 'Synchronizing time-series channels from ISRO SPACE-03 ingestion pipeline',
  heightClass = 'min-h-[260px]',
}) => {
  return (
    <div className={`sat-panel flex flex-col items-center justify-center p-8 text-center ${heightClass}`}>
      <div className="relative mb-4">
        {/* Aerospace radar sweep ring */}
        <div className="w-14 h-14 rounded-full border border-cyan-500/30 flex items-center justify-center">
          <div className="w-10 h-10 rounded-full border border-cyan-400/50 border-t-cyan-400 animate-spin flex items-center justify-center">
            <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
          </div>
        </div>
      </div>
      <h4 className="text-sm font-mono font-medium text-slate-200 tracking-wide">{message}</h4>
      <p className="text-xs text-slate-400 max-w-sm mt-1">{submessage}</p>
    </div>
  );
};

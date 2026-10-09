import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  heightClass?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Telemetry Stream Synchronization Failed',
  message = 'Unable to fetch telemetry packets from API. Check connection to satellite ground station bridge.',
  onRetry,
  heightClass = 'min-h-[240px]',
}) => {
  return (
    <div className={`sat-panel flex flex-col items-center justify-center p-8 text-center ${heightClass} border-rose-500/30 bg-rose-950/10`}>
      <div className="p-3 rounded-full border border-rose-500/40 bg-rose-950/40 text-rose-400 mb-3">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h4 className="text-sm font-semibold text-rose-300 font-mono">{title}</h4>
      <p className="text-xs text-slate-400 max-w-md mt-1">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded bg-[#182642] hover:bg-[#20345B] text-slate-200 border border-[#2D4573] transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>RETRY CONNECTION</span>
        </button>
      )}
    </div>
  );
};

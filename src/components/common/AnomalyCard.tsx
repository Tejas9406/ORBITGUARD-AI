import React from 'react';
import type { AnomalyEvent } from '../../types/anomaly';
import { SeverityBadge } from './SeverityBadge';
import { ArrowRight, AlertOctagon } from 'lucide-react';

interface AnomalyCardProps {
  anomaly: AnomalyEvent;
  isSelected?: boolean;
  onClick?: () => void;
  onInvestigate?: (anomaly: AnomalyEvent) => void;
  className?: string;
}

export const AnomalyCard: React.FC<AnomalyCardProps> = ({
  anomaly,
  isSelected = false,
  onClick,
  onInvestigate,
  className = '',
}) => {
  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`sat-glass-card p-3.5 transition-all duration-150 group ${
        isSelected
          ? 'border-cyan-400 bg-[#142340] shadow-[0_0_15px_rgba(0,229,255,0.22)]'
          : 'hover:border-[#2A4470] hover:bg-[#0D182E]'
      } ${onClick ? 'cursor-pointer focus:outline-none focus:ring-1 focus:ring-cyan-400' : ''} ${className}`}
    >
      <div className="flex items-center justify-between text-xs mb-1.5">
        <div className="flex items-center gap-1.5">
          <AlertOctagon className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span className="font-mono font-bold text-slate-100 group-hover:text-cyan-300">
            {anomaly.id}
          </span>
          <span className="text-slate-400 font-mono text-[11px]">• {anomaly.channelId}</span>
        </div>
        <SeverityBadge severity={anomaly.severity} size="sm" />
      </div>

      <p className="text-xs text-slate-300 line-clamp-1 mb-2 font-medium">{anomaly.title}</p>

      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-[#182C4C]/80">
        <span>
          Score: <b className="text-rose-400 font-mono">{anomaly.anomalyScore}</b>
        </span>
        <div className="flex items-center gap-2">
          <span>{anomaly.timestamp}</span>
          {onInvestigate && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onInvestigate(anomaly);
              }}
              className="text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5 text-[10px]"
              title="Investigate anomaly"
            >
              <span>Inspect</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

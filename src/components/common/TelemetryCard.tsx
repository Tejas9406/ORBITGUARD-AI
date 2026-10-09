import React from 'react';
import type { TelemetryChannel } from '../../types/telemetry';
import { StatusBadge } from './StatusBadge';
import { Activity } from 'lucide-react';

interface TelemetryCardProps {
  channel: TelemetryChannel;
  isSelected?: boolean;
  onClick?: () => void;
  className?: string;
}

export const TelemetryCard: React.FC<TelemetryCardProps> = ({
  channel,
  isSelected = false,
  onClick,
  className = '',
}) => {
  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`sat-glass-card p-3.5 transition-all duration-150 ${
        isSelected
          ? 'border-cyan-400 bg-[#122240] shadow-[0_0_15px_rgba(0,229,255,0.25)]'
          : 'hover:border-[#223B64] hover:bg-[#0E1A33]'
      } ${onClick ? 'cursor-pointer focus:outline-none focus:ring-1 focus:ring-cyan-400' : ''} ${className}`}
    >
      <div className="flex items-center justify-between text-xs mb-1.5">
        <span className="font-mono font-bold text-cyan-300 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          {channel.id}
        </span>
        <StatusBadge status={channel.status} size="sm" />
      </div>

      <h4 className="text-xs font-medium text-slate-200 line-clamp-1 mb-0.5">{channel.name}</h4>
      <span className="text-[10px] font-mono text-slate-400 block mb-2">{channel.subsystem}</span>

      <div className="flex items-baseline justify-between pt-2 border-t border-[#182C4C]/80 text-xs font-mono">
        <span className="text-slate-400">Telemetry:</span>
        <span className="font-bold text-slate-100 text-sm">
          {channel.currentValue} <span className="text-xs text-slate-400 font-normal">{channel.unit}</span>
        </span>
      </div>
    </div>
  );
};

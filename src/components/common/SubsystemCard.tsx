import React from 'react';
import type { SubsystemHealth } from '../../types/health';
import { StatusBadge } from './StatusBadge';
import { ArrowDownRight, ArrowUpRight, Minus, Zap, Thermometer, Compass, Radio } from 'lucide-react';

interface SubsystemCardProps {
  subsystem: SubsystemHealth;
  isSelected?: boolean;
  onClick?: () => void;
  className?: string;
}

export const SubsystemCard: React.FC<SubsystemCardProps> = ({
  subsystem,
  isSelected = false,
  onClick,
  className = '',
}) => {
  const { id, name, shortCode, healthScore, status, trend, primaryMetric, activeAnomalyCount } = subsystem;

  const isDegrading = trend === 'DEGRADING';
  const isRecovering = trend === 'RECOVERING' || trend === 'IMPROVING';

  const SubIcon = {
    power: Zap,
    thermal: Thermometer,
    aocs: Compass,
    ttc: Radio,
  }[id] || Zap;

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`sat-glass-card p-4 flex flex-col justify-between transition-all duration-200 ${
        isSelected
          ? 'border-cyan-400 bg-[#122240] shadow-[0_0_16px_rgba(0,229,255,0.25)]'
          : 'hover:border-[#223B64] hover:bg-[#0E1A33]'
      } ${onClick ? 'cursor-pointer focus:outline-none focus:ring-1 focus:ring-cyan-400' : ''} ${className}`}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1 rounded bg-[#101D36] text-cyan-400 border border-[#1C3258]">
              <SubIcon className="w-3.5 h-3.5" />
            </div>
            <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-[#091224] text-cyan-300 border border-[#16294A]">
              {shortCode}
            </span>
            <h4 className="text-xs font-semibold text-slate-200">{name}</h4>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            {primaryMetric.label}: <span className="font-mono text-slate-300">{primaryMetric.value}</span>
          </p>
        </div>
        <StatusBadge status={status} size="sm" showPulse={activeAnomalyCount > 0} />
      </div>

      <div className="flex items-end justify-between pt-2.5 border-t border-[#182C4C]/80">
        <div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Health Index</span>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-2xl font-mono font-bold ${
                healthScore >= 90
                  ? 'text-emerald-400'
                  : healthScore >= 75
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {healthScore}
            </span>
            <span className="text-xs font-mono text-slate-400">/100</span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {activeAnomalyCount > 0 && (
            <span className="text-[11px] font-mono text-rose-400 bg-rose-950/60 border border-rose-500/40 px-2 py-0.5 rounded">
              {activeAnomalyCount} Anomaly
            </span>
          )}

          <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
            {isDegrading && (
              <span className="flex items-center text-rose-400">
                <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
                Degrading
              </span>
            )}
            {isRecovering && (
              <span className="flex items-center text-emerald-400">
                <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                Recovering
              </span>
            )}
            {!isDegrading && !isRecovering && (
              <span className="flex items-center text-slate-400">
                <Minus className="w-3.5 h-3.5 mr-0.5" />
                Stable
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

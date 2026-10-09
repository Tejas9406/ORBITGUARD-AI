import type { LucideIcon } from 'lucide-react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle: string;
  statusText?: string;
  statusVariant?: 'nominal' | 'attention' | 'critical' | 'info';
  icon: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  tag?: string;
  onClick?: () => void;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  unit,
  subtitle,
  statusText,
  statusVariant = 'info',
  icon: Icon,
  trend,
  trendValue,
  tag,
  onClick,
}) => {
  const borderStyles = {
    nominal: 'hover:border-emerald-500/50',
    attention: 'border-amber-500/40 bg-amber-950/15 hover:border-amber-500/70',
    critical: 'border-rose-500/50 bg-rose-950/20 hover:border-rose-500/80 shadow-[0_0_16px_-3px_rgba(239,68,68,0.25)]',
    info: 'hover:border-cyan-500/50',
  }[statusVariant];

  const badgeStyles = {
    nominal: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
    attention: 'text-amber-400 bg-amber-950/60 border-amber-500/40',
    critical: 'text-rose-400 bg-rose-950/70 border-rose-500/50',
    info: 'text-cyan-400 bg-cyan-950/60 border-cyan-500/30',
  }[statusVariant];

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`sat-glass-card p-4 flex flex-col justify-between transition-all duration-200 ${borderStyles} ${
        onClick ? 'cursor-pointer hover:bg-[#111F38] focus:outline-none focus:ring-1 focus:ring-cyan-400' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-[#15213B] text-cyan-400 border border-[#243657]">
            <Icon className="w-4 h-4" />
          </div>
          <span className="text-xs font-mono tracking-wider uppercase text-slate-400">{title}</span>
        </div>
        {tag && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            {tag}
          </span>
        )}
      </div>

      <div className="my-1">
        <div className="flex items-baseline gap-1.5">
          <span className="text-3xl font-mono font-bold text-slate-100 tracking-tight">{value}</span>
          {unit && <span className="text-sm font-mono text-slate-400">{unit}</span>}
        </div>
      </div>

      <div className="flex items-center justify-between text-xs pt-2 border-t border-[#1E2D4A]/60 mt-1">
        <span className="text-slate-400 truncate pr-2">{subtitle}</span>
        {statusText && (
          <span className={`font-mono text-[11px] px-2 py-0.5 rounded border uppercase shrink-0 font-medium ${badgeStyles}`}>
            {statusText}
          </span>
        )}
        {trend && (
          <div className="flex items-center gap-1 font-mono text-[11px] text-slate-400 shrink-0">
            {trend === 'up' && <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />}
            {trend === 'down' && <ArrowDownRight className="w-3.5 h-3.5 text-rose-400" />}
            {trend === 'neutral' && <Minus className="w-3.5 h-3.5 text-slate-400" />}
            <span>{trendValue}</span>
          </div>
        )}
      </div>
    </div>
  );
};

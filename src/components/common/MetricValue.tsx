import React from 'react';

interface MetricValueProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral';
  status?: 'nominal' | 'warning' | 'critical' | 'neutral';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const MetricValue: React.FC<MetricValueProps> = ({
  label,
  value,
  unit,
  delta,
  deltaType = 'neutral',
  status = 'neutral',
  size = 'md',
  className = '',
}) => {
  const valueColor = {
    nominal: 'text-emerald-400',
    warning: 'text-amber-400',
    critical: 'text-rose-400',
    neutral: 'text-slate-100',
  }[status];

  const sizeClass = {
    sm: 'text-sm font-semibold',
    md: 'text-lg font-bold',
    lg: 'text-2xl font-bold tracking-tight',
    xl: 'text-3xl md:text-4xl font-extrabold tracking-tight',
  }[size];

  const deltaColor = {
    positive: 'text-emerald-400',
    negative: 'text-rose-400',
    neutral: 'text-slate-400',
  }[deltaType];

  return (
    <div className={`flex flex-col ${className}`}>
      <span className="text-[10px] font-mono tracking-wider uppercase text-slate-400 mb-0.5">
        {label}
      </span>
      <div className="flex items-baseline gap-1.5">
        <span className={`font-mono ${valueColor} ${sizeClass}`}>{value}</span>
        {unit && <span className="text-xs font-mono text-slate-400">{unit}</span>}
        {delta && (
          <span className={`text-[11px] font-mono ml-1 ${deltaColor}`}>
            {delta}
          </span>
        )}
      </div>
    </div>
  );
};

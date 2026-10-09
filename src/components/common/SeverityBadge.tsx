import { AlertOctagon, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { AnomalySeverity } from '../../types/anomaly';

interface SeverityBadgeProps {
  severity: AnomalySeverity;
  size?: 'sm' | 'md' | 'lg';
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, size = 'md' }) => {
  let bg = 'bg-slate-800/80';
  let border = 'border-slate-700';
  let text = 'text-slate-300';
  let Icon = Info;

  switch (severity) {
    case 'CRITICAL':
      bg = 'bg-rose-950/80';
      border = 'border-rose-500/70';
      text = 'text-rose-400 font-bold';
      Icon = AlertOctagon;
      break;
    case 'HIGH':
      bg = 'bg-orange-950/80';
      border = 'border-orange-500/70';
      text = 'text-orange-400 font-semibold';
      Icon = AlertTriangle;
      break;
    case 'MEDIUM':
      bg = 'bg-amber-950/80';
      border = 'border-amber-500/60';
      text = 'text-amber-300 font-medium';
      Icon = AlertCircle;
      break;
    case 'LOW':
      bg = 'bg-blue-950/60';
      border = 'border-blue-500/40';
      text = 'text-blue-300';
      Icon = Info;
      break;
  }

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded border font-mono tracking-wider ${bg} ${border} ${text} ${sizeClasses}`}
      aria-label={`Severity: ${severity}`}
    >
      <Icon className={iconSizes} aria-hidden="true" />
      <span>{severity}</span>
    </span>
  );
};

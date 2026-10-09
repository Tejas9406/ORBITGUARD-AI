import { CheckCircle2, AlertTriangle, AlertOctagon, Info, Radio } from 'lucide-react';

export type StatusType =
  | 'NOMINAL'
  | 'GOOD'
  | 'ATTENTION'
  | 'WARNING'
  | 'CRITICAL'
  | 'ONLINE'
  | 'OFFLINE'
  | 'STANDBY'
  | 'ACTIVE'
  | 'RESOLVED';

interface StatusBadgeProps {
  status: StatusType | string;
  size?: 'sm' | 'md' | 'lg';
  showPulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showPulse = false,
}) => {
  const norm = status.toUpperCase();

  let bg = 'bg-slate-800/80';
  let border = 'border-slate-700';
  let text = 'text-slate-300';
  let Icon = Info;
  let pulseColor = 'bg-slate-400';

  if (norm === 'NOMINAL' || norm === 'GOOD' || norm === 'ONLINE' || norm === 'RESOLVED') {
    bg = 'bg-emerald-950/60';
    border = 'border-emerald-500/40';
    text = 'text-emerald-400';
    Icon = CheckCircle2;
    pulseColor = 'bg-emerald-400';
  } else if (norm === 'ATTENTION' || norm === 'WARNING' || norm === 'STANDBY') {
    bg = 'bg-amber-950/60';
    border = 'border-amber-500/50';
    text = 'text-amber-400';
    Icon = AlertTriangle;
    pulseColor = 'bg-amber-400';
  } else if (norm === 'CRITICAL' || norm === 'OFFLINE' || norm === 'ACTIVE') {
    bg = 'bg-rose-950/70';
    border = 'border-rose-500/60';
    text = 'text-rose-400';
    Icon = AlertOctagon;
    pulseColor = 'bg-rose-500';
  } else if (norm === 'PROCESSING' || norm === 'STREAMING') {
    bg = 'bg-cyan-950/60';
    border = 'border-cyan-500/40';
    text = 'text-cyan-400';
    Icon = Radio;
    pulseColor = 'bg-cyan-400';
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2 font-medium',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded border font-mono tracking-wide ${bg} ${border} ${text} ${sizeClasses}`}
      role="status"
    >
      {showPulse && (
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${pulseColor}`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${pulseColor}`} />
        </span>
      )}
      <Icon className={iconSizes} aria-hidden="true" />
      <span>{status}</span>
    </span>
  );
};

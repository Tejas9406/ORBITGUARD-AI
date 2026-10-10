import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  badge?: string;
  actions?: React.ReactNode;
  className?: string;
  dotColor?: 'cyan' | 'red' | 'amber' | 'emerald';
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  subtitle,
  icon: Icon,
  badge,
  actions,
  className = '',
  dotColor = 'cyan',
}) => {
  const dotColorClass = {
    cyan: 'bg-cyan-400 shadow-[0_0_8px_#00E5FF]',
    red: 'bg-rose-500 shadow-[0_0_8px_#EF4444]',
    amber: 'bg-amber-400 shadow-[0_0_8px_#F59E0B]',
    emerald: 'bg-emerald-400 shadow-[0_0_8px_#10B981]',
  }[dotColor];

  return (
    <div className={`flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-[#1A2E50]/70 gap-2 ${className}`}>
      <div className="flex items-center gap-2.5">
        <span className={`w-2 h-2 rounded-full ${dotColorClass}`} />
        {Icon && <Icon className="w-4 h-4 text-cyan-400" />}
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-sm md:text-base font-semibold tracking-wider text-slate-100 uppercase">
              {title}
            </h3>
            {badge && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/40">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[11px] font-mono text-slate-400 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>

      {actions && <div className="flex items-center gap-2 self-end sm:self-auto">{actions}</div>}
    </div>
  );
};

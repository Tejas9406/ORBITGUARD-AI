import type { LucideIcon } from 'lucide-react';
import { Database } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  statusVariant?: 'nominal' | 'neutral' | 'search';
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Database,
  title,
  message,
  actionLabel,
  onAction,
  statusVariant = 'neutral',
}) => {
  const iconColors = {
    nominal: 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30',
    neutral: 'text-slate-400 bg-slate-900 border-slate-700',
    search: 'text-cyan-400 bg-cyan-950/40 border-cyan-500/30',
  }[statusVariant];

  return (
    <div className="sat-panel flex flex-col items-center justify-center p-8 text-center min-h-[240px]">
      <div className={`p-3 rounded-full border mb-3 ${iconColors}`}>
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
      <p className="text-xs text-slate-400 max-w-sm mt-1">{message}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-3 py-1.5 text-xs font-mono font-medium rounded bg-[#15213B] hover:bg-[#1E2D4A] text-cyan-300 border border-cyan-500/30 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

import React from 'react';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  glow?: 'cyan' | 'red' | 'amber' | 'none';
  variant?: 'default' | 'accent' | 'elevated' | 'danger' | 'warning';
  cornerAccents?: boolean;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  onClick?: () => void;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  className = '',
  glow,
  variant = 'default',
  cornerAccents = false,
  header,
  footer,
  onClick,
  padding,
}) => {
  // Resolve effective glow from either variant or glow prop
  const effectiveGlow = glow || (
    variant === 'danger' ? 'red' :
    variant === 'warning' ? 'amber' :
    variant === 'accent' ? 'cyan' : 'none'
  );

  const glowClasses = {
    none: '',
    cyan: 'shadow-[0_0_18px_-2px_rgba(0,229,255,0.22)] border-cyan-500/40',
    red: 'shadow-[0_0_18px_-2px_rgba(239,68,68,0.25)] border-rose-500/45',
    amber: 'shadow-[0_0_18px_-2px_rgba(245,158,11,0.22)] border-amber-500/40',
  }[effectiveGlow];

  // If className has custom padding or padding is explicitly passed
  const effectivePadding = padding !== undefined ? padding : (className.includes('p-') ? 'none' : 'md');

  const paddingClasses = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-4 md:p-5',
    lg: 'p-6',
  }[effectivePadding];

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`sat-glass-card relative flex flex-col transition-all duration-200 ${glowClasses} ${
        cornerAccents ? 'sat-corner-accents' : ''
      } ${
        onClick
          ? 'cursor-pointer hover:border-cyan-400/60 focus:outline-none focus:ring-1 focus:ring-cyan-400'
          : ''
      } ${className}`}
    >
      {header && (
        <div className="px-4 py-3 border-b border-[#1A2E50]/70 flex items-center justify-between">
          {header}
        </div>
      )}

      <div className={`flex-1 ${paddingClasses}`}>{children}</div>

      {footer && (
        <div className="px-4 py-2.5 border-t border-[#1A2E50]/70 bg-[#070D1B]/40 text-xs font-mono text-slate-400">
          {footer}
        </div>
      )}
    </div>
  );
};

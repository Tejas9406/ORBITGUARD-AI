import React from 'react';

interface HealthGaugeProps {
  score: number; // 0 to 100
  size?: number; // width & height in px
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  showDetails?: boolean;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({
  score,
  size = 180,
  strokeWidth = 14,
  label = 'SYSTEM HEALTH',
  sublabel,
  showDetails = true,
}) => {
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  // Arc angle (270 degrees arc)
  const arcLength = circumference * 0.75;
  const strokeDashoffset = arcLength - (arcLength * clampedScore) / 100;

  let color = '#10B981'; // Teal / Green
  let glowColor = 'rgba(16, 185, 129, 0.3)';
  let statusText = 'NOMINAL';

  if (clampedScore < 70) {
    color = '#EF4444'; // Red
    glowColor = 'rgba(239, 68, 68, 0.4)';
    statusText = 'CRITICAL';
  } else if (clampedScore < 85) {
    color = '#F59E0B'; // Amber
    glowColor = 'rgba(245, 158, 11, 0.35)';
    statusText = 'ATTENTION';
  }

  return (
    <div className="flex flex-col items-center justify-center relative">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-[135deg]"
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#182642"
          strokeWidth={strokeWidth}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Active progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{
            filter: `drop-shadow(0 0 6px ${glowColor})`,
            transition: 'stroke-dashoffset 0.8s ease-out, stroke 0.4s ease',
          }}
        />
      </svg>

      {/* Center readout */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-4xl md:text-5xl font-mono font-bold tracking-tighter text-slate-100">
          {clampedScore}
          <span className="text-sm font-sans text-slate-400 font-normal ml-0.5">/100</span>
        </span>
        <span
          className="text-xs font-mono font-semibold tracking-wider uppercase px-2 py-0.5 rounded mt-1"
          style={{ color, backgroundColor: `${color}1A` }}
        >
          {statusText}
        </span>
        {label && <span className="text-[10px] tracking-widest text-slate-400 uppercase mt-1">{label}</span>}
      </div>

      {showDetails && sublabel && (
        <span className="text-xs font-mono text-slate-400 mt-2 text-center">{sublabel}</span>
      )}
    </div>
  );
};

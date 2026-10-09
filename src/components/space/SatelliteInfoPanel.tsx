import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { StatusBadge } from '../common/StatusBadge';
import type { SatelliteStatus } from '../../types/satellite';
import {
  Satellite,
  AlertOctagon,
  ArrowRight,
  Activity,
  X,
  Clock,
} from 'lucide-react';

interface SatelliteInfoPanelProps {
  satelliteId?: string;
  orbitType?: string;
  altitudeKm?: number;
  latitude?: number;
  longitude?: number;
  status?: SatelliteStatus;
  healthScore?: number;
  activeAnomaliesCount?: number;
  lastTelemetryUpdate?: string;
  onViewTelemetry?: () => void;
  onInvestigateAnomaly?: () => void;
  onClose?: () => void;
  className?: string;
}

export const SatelliteInfoPanel: React.FC<SatelliteInfoPanelProps> = ({
  satelliteId = 'SATSHIELD-OBS-1',
  orbitType = 'Polar Sun-Synchronous LEO (~550 km)',
  altitudeKm = 552.4,
  latitude = 18.42,
  longitude = 78.53,
  status = 'CRITICAL',
  healthScore = 84,
  activeAnomaliesCount = 2,
  lastTelemetryUpdate = '10:54:20 UTC',
  onViewTelemetry,
  onInvestigateAnomaly,
  onClose,
  className = '',
}) => {
  const latStr = `${Math.abs(latitude).toFixed(2)}° ${latitude >= 0 ? 'N' : 'S'}`;
  const lonStr = `${Math.abs(longitude).toFixed(2)}° ${longitude >= 0 ? 'E' : 'W'}`;

  return (
    <GlassPanel
      cornerAccents={true}
      glow={status === 'CRITICAL' ? 'red' : status === 'WARNING' ? 'amber' : 'cyan'}
      className={`sat-glass-card border-cyan-500/40 bg-[#070D1C]/95 p-4 shadow-2xl backdrop-blur-md ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#1A2E50]/80">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded bg-cyan-950/70 border border-cyan-500/50 text-cyan-400">
            <Satellite className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-mono text-sm font-bold text-slate-100">{satelliteId}</h4>
              <StatusBadge status={status} size="sm" showPulse={status !== 'NOMINAL'} />
            </div>
            <span className="text-[10px] font-mono text-slate-400 block mt-0.5">{orbitType}</span>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            aria-label="Close satellite information"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Orbit & Subsatellite Metrics */}
      <div className="grid grid-cols-2 gap-2.5 my-3 text-xs font-mono">
        <div className="p-2 rounded bg-[#0A1224] border border-[#16294A]">
          <span className="text-[10px] text-slate-400 uppercase block">Orbital Altitude</span>
          <span className="text-sm font-bold text-slate-100">{altitudeKm} km</span>
        </div>
        <div className="p-2 rounded bg-[#0A1224] border border-[#16294A]">
          <span className="text-[10px] text-slate-400 uppercase block">Ground Track Subpoint</span>
          <span className="text-xs font-bold text-cyan-300">{latStr}, {lonStr}</span>
        </div>
        <div className="p-2 rounded bg-[#0A1224] border border-[#16294A]">
          <span className="text-[10px] text-slate-400 uppercase block">Subsystem Health</span>
          <span className={`text-sm font-bold ${healthScore < 75 ? 'text-rose-400' : healthScore < 85 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {healthScore} / 100
          </span>
        </div>
        <div className="p-2 rounded bg-[#0A1224] border border-[#16294A]">
          <span className="text-[10px] text-slate-400 uppercase block">Active Anomalies</span>
          <span className="text-sm font-bold text-rose-400 flex items-center gap-1">
            <AlertOctagon className="w-3.5 h-3.5" />
            {activeAnomaliesCount} Active
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 py-1.5 px-2 rounded bg-[#060B17] border border-[#13223E] mb-3">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-cyan-400" />
          Last Ingest: {lastTelemetryUpdate}
        </span>
        <span className="text-emerald-400">TELEMETRY: 1Hz</span>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 border-t border-[#16294A]/70">
        {onViewTelemetry && (
          <button
            onClick={onViewTelemetry}
            className="py-1.5 px-3 rounded bg-[#13233F] hover:bg-[#1A3056] text-cyan-300 text-xs font-mono font-medium border border-cyan-500/40 flex items-center justify-center gap-1.5 transition-colors"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>VIEW TELEMETRY</span>
          </button>
        )}

        {onInvestigateAnomaly && (
          <button
            onClick={onInvestigateAnomaly}
            className="py-1.5 px-3 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-bold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
          >
            <span>INVESTIGATE ANOMALY</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </GlassPanel>
  );
};

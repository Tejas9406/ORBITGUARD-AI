import { useState } from 'react';
import {
  Menu,
  Bell,
  Satellite,
  Clock,
  Home,
} from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { Link } from 'react-router-dom';

interface TopBarProps {
  onOpenMobileMenu: () => void;
  isAttentionRequired?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  onOpenMobileMenu,
  isAttentionRequired = true,
}) => {
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="h-16 bg-[#090E1B] border-b border-[#1E2D4A] px-4 md:px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Mobile trigger & Active Mission */}
      <div className="flex items-center gap-4">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 rounded hover:bg-slate-800 text-slate-300"
          aria-label="Open mobile menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="hidden sm:flex items-center justify-center w-8 h-8 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-400">
            <Satellite className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-slate-100">
                SATSHIELD-OBS-1
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-500/30">
                LEO 550km
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400 block truncate">
              Mission: ISRO SPACE-03 Telemetry Stream Pass #0924
            </span>
          </div>
        </div>
      </div>

      {/* Right: Status, Time, Alerts, Profile */}
      <div className="flex items-center gap-3 md:gap-5">
        {/* Telemetry Stream Mode Indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#090F1C] border border-cyan-500/30 text-[10px] font-mono text-cyan-300 shadow-sm" title="Telemetry Stream Mode: High-Fidelity Simulated ISRO SPACE-03 Telemetry">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span>DATA: SIMULATED PASS</span>
        </div>

        {/* Live System Status */}
        <div className="hidden md:flex items-center gap-2">
          <StatusBadge
            status={isAttentionRequired ? 'ATTENTION' : 'NOMINAL'}
            size="sm"
            showPulse={true}
          />
        </div>

        {/* Universal Mission Time UTC */}
        <div className="hidden sm:flex items-center gap-1.5 font-mono text-xs text-slate-300 bg-[#0F172A] px-2.5 py-1 rounded border border-[#1E2D4A]">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>10:54:20 UTC</span>
        </div>

        {/* Landing Page Link */}
        <Link
          to="/"
          className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0A162C] hover:bg-[#112344] border border-[#1E355B] hover:border-cyan-400 text-slate-300 hover:text-white text-xs font-mono transition-colors"
          title="Return to SatShield Landing Page"
        >
          <Home className="w-3.5 h-3.5 text-cyan-400" />
          <span>Landing</span>
        </Link>

        {/* Active Alerts Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications((prev) => !prev)}
            className="relative p-2 rounded hover:bg-slate-800 text-slate-300 transition-colors focus:ring-1 focus:ring-cyan-400 focus:outline-none"
            aria-label="View system notifications"
            aria-expanded={showNotifications}
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-[#090E1B]" />
          </button>

          {showNotifications && (
            <div
              className="absolute right-0 mt-2 w-80 sat-panel border-cyan-500/40 bg-[#0F172A] shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95"
              role="menu"
            >
              <div className="flex items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2">
                <span className="font-mono text-xs font-bold text-slate-200">ACTIVE FLIGHT ALERTS</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-500/40">
                  2 UNRESOLVED
                </span>
              </div>
              <div className="space-y-2">
                <Link
                  to="/anomalies?id=ANM-0047"
                  onClick={() => setShowNotifications(false)}
                  className="block p-2 rounded bg-rose-950/30 border border-rose-500/40 hover:bg-rose-900/30 transition-colors"
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-rose-400 font-bold">ANM-0047: CRITICAL</span>
                    <span className="text-slate-400 text-[10px]">10:51 UTC</span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">Solar Array Bus Voltage Sag (-4.2V)</p>
                </Link>

                <Link
                  to="/anomalies?id=ANM-0046"
                  onClick={() => setShowNotifications(false)}
                  className="block p-2 rounded bg-amber-950/30 border border-amber-500/40 hover:bg-amber-900/30 transition-colors"
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-amber-400 font-bold">ANM-0046: HIGH</span>
                    <span className="text-slate-400 text-[10px]">10:49 UTC</span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">Battery Pack #2 Thermal Excursion</p>
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Flight Controller Profile */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#1E2D4A]/70">
          <div className="w-7 h-7 rounded-full bg-[#182642] border border-cyan-500/40 flex items-center justify-center text-cyan-400 text-xs font-mono font-bold">
            OP
          </div>
          <div className="hidden xl:flex flex-col text-left">
            <span className="text-xs font-medium text-slate-200 leading-tight">Flight Console</span>
            <span className="text-[10px] font-mono text-cyan-400">ISRO-OPERATOR-1</span>
          </div>
        </div>
      </div>
    </header>
  );
};

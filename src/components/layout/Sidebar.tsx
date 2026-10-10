import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  AlertOctagon,
  HeartPulse,
  PlayCircle,
  History,
  Settings,
  Shield,
  Radio,
  Server,
  ChevronLeft,
  ChevronRight,
  Database,
} from 'lucide-react';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  const navItems = [
    { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    { name: 'Telemetry Explorer', to: '/telemetry', icon: Activity },
    { name: 'Custom Upload', to: '/upload', icon: Database },
    { name: 'Anomalies', to: '/anomalies', icon: AlertOctagon },
    { name: 'Subsystem Health', to: '/health', icon: HeartPulse },
    { name: 'Telemetry Replay', to: '/replay', icon: PlayCircle },
    { name: 'Mission History', to: '/history', icon: History },
    { name: 'Settings', to: '/settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-40 lg:hidden backdrop-blur-xs"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 bg-[#0A0F1E] border-r border-[#1E2D4A] flex flex-col transition-all duration-300 ${
          isCollapsed ? 'w-20' : 'w-64'
        } ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Logo / Brand Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#1E2D4A] bg-[#070B14]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-400/50 flex items-center justify-center shrink-0 shadow-[0_0_12px_rgba(0,229,255,0.25)]">
              <Shield className="w-5 h-5 text-cyan-400" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col truncate">
                <span className="font-mono font-bold text-base tracking-wider text-slate-100 flex items-center gap-1.5">
                  ORBIT<span className="text-cyan-400">GUARD</span>
                </span>
                <span className="text-[10px] tracking-tight text-slate-400 truncate">
                  GENERIC TELEMETRY PLATFORM
                </span>
              </div>
            )}
          </div>

          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Tagline Bar */}
        {!isCollapsed && (
          <div className="px-4 py-2 bg-[#0C1425] border-b border-[#1E2D4A]/50 text-[11px] font-mono text-cyan-400/90 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="truncate">Smarter Telemetry. Safer Missions.</span>
          </div>
        )}

        {/* Navigation list */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-mono tracking-wide transition-all duration-150 ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-950/80 to-[#122442] text-cyan-300 border-l-2 border-cyan-400 font-semibold shadow-[inset_0_1px_0_rgba(0,229,255,0.15)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#111C30]'
                  }`
                }
              >
                <Icon className={`w-4 h-4 shrink-0`} />
                {!isCollapsed && <span className="truncate flex-1">{item.name}</span>}
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom Section: System Status & API Mode */}
        <div className="p-3 border-t border-[#1E2D4A] bg-[#080D1A] space-y-2">
          {!isCollapsed ? (
            <>
              <div className="space-y-1.5 text-[11px] font-mono">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-cyan-400" />
                    Stream:
                  </span>
                  <span className="text-slate-300 font-medium">SOURCE-DEPENDENT</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-cyan-400" />
                    AI Engine:
                  </span>
                  <span className="text-cyan-400 font-medium">ORBITGUARD CORE</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-cyan-400" />
                    Backend API:
                  </span>
                  <span className="text-amber-400 font-medium">CHECK /api/health</span>
                </div>
              </div>

              <div className="pt-2 border-t border-[#1E2D4A]/60 flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Analysis state is run-scoped</span>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center gap-2 py-1">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400" title="State shown in page" />
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

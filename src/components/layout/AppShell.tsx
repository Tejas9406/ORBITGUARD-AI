import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { AlertBanner } from '../common/AlertBanner';

export const AppShell: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);
  const [dismissAlert, setDismissAlert] = useState<boolean>(false);

  return (
    <div className="min-h-screen bg-[#070B14] text-slate-100 flex flex-col font-sans">
      {/* Sidebar */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          isSidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64'
        }`}
      >
        <TopBar
          onOpenMobileMenu={() => setIsMobileOpen(true)}
          isAttentionRequired={true}
        />

        {/* Global Active Anomaly Banner */}
        {!dismissAlert && (
          <div className="px-4 md:px-6 pt-4">
            <AlertBanner
              anomalyId="ANM-0047"
              channelName="Channel_04: Solar Array Bus Voltage"
              severity="CRITICAL"
              message="Active anomaly detected: -4.2V deviation in power bus voltage envelope during eclipse transition."
              onInvestigate={() => setDismissAlert(false)}
            />
          </div>
        )}

        {/* Page Content Body */}
        <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        {/* Aerospace Mission Control Footer */}
        <footer className="mt-auto border-t border-[#1E2D4A] bg-[#0A0F1E] px-4 md:px-6 py-3 text-xs font-mono text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>SATSHIELD Telemetry Intelligence Platform</span>
            <span className="hidden sm:inline text-slate-400">•</span>
            <span className="hidden sm:inline text-slate-400">ISRO SPACE-03 Specification</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>FastAPI Integration Ready</span>
            <span>LEO Ground Pass: #0924</span>
          </div>
        </footer>
      </div>
    </div>
  );
};

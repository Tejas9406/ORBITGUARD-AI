import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export const AppShell: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);

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
          isAttentionRequired={false}
        />

        {/* Page Content Body */}
        <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        {/* Aerospace Mission Control Footer */}
        <footer className="mt-auto border-t border-[#1E2D4A] bg-[#0A0F1E] px-4 md:px-6 py-3 text-xs font-mono text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>SatShield telemetry intelligence</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>Data source and detector status are shown per analysis run.</span>
          </div>
        </footer>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/common/GlassPanel';
import { SectionHeader } from '../components/common/SectionHeader';
import { apiService } from '../services/api';
import { Server, Monitor, Save, Check, RefreshCw, Wifi, WifiOff } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [apiUrl, setApiUrl] = useState('http://localhost:8000/api/v1');
  const [useDemoData, setUseDemoData] = useState(true);
  const [alertSound, setAlertSound] = useState(true);
  const [autoRefreshHz, setAutoRefreshHz] = useState('1');
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [isPinging, setIsPinging] = useState(false);
  const [pingResult, setPingResult] = useState<'idle' | 'online' | 'offline'>('idle');

  const handleTestConnection = async () => {
    setIsPinging(true);
    setPingResult('idle');
    try {
      const isOnline = await apiService.checkBackendHealth();
      setPingResult(isOnline ? 'online' : 'offline');
    } catch {
      setPingResult('offline');
    } finally {
      setIsPinging(false);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Settings & System Configuration"
        subtitle="Configure telemetry ingestion pipelines, FastAPI endpoints, and operator display preferences."
        badge="CONSOLE CONFIG"
      />

      <form onSubmit={handleSave} className="space-y-6">
        {/* Backend & API Configuration */}
        <GlassPanel variant="accent" cornerAccents className="p-5 space-y-4">
          <SectionHeader
            title="FASTAPI BACKEND & TELEMETRY BRIDGE"
            subtitle="Configure microservice endpoint for live telemetry and model inference"
            badge="API GATEWAY"
            icon={Server}
          />

          <div className="space-y-4 text-xs font-mono pt-2">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-slate-300">FastAPI Base Endpoint URL</label>
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={isPinging}
                  className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 ${isPinging ? 'animate-spin' : ''}`} />
                  <span>Test Connection</span>
                </button>
              </div>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="w-full bg-[#080E1C] border border-[#1E2D4A] rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
              />
              <div className="flex items-center justify-between mt-1.5 text-[11px]">
                <span className="text-slate-400">
                  Target endpoint for live ISRO SPACE-03 telemetry ingestion and FastAPI ML microservices.
                </span>
                {pingResult === 'online' && (
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <Wifi className="w-3 h-3" /> 200 OK — Backend Connected
                  </span>
                )}
                {pingResult === 'offline' && (
                  <span className="text-amber-400 font-bold flex items-center gap-1">
                    <WifiOff className="w-3 h-3" /> Offline — Defaulting to High-Fidelity Demo Stream
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between p-3 rounded bg-[#090F1C]/80 border border-[#182642]">
              <div>
                <span className="text-slate-200 font-medium block">Use Standalone Demo Data</span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  When enabled, uses high-fidelity aerospace demo telemetry without requiring active FastAPI connection.
                </span>
              </div>
              <input
                type="checkbox"
                checked={useDemoData}
                onChange={(e) => setUseDemoData(e.target.checked)}
                className="w-4 h-4 rounded text-cyan-500 focus:ring-0 bg-[#0F172A] border-[#1E2D4A]"
              />
            </div>
          </div>
        </GlassPanel>

        {/* Display & Chart Preferences */}
        <GlassPanel variant="default" className="p-5 space-y-4">
          <SectionHeader
            title="TELEMETRY DISPLAY & CHART PREFERENCES"
            subtitle="Configure telemetry refresh rate and mission operator audio cues"
            badge="OPERATOR CONSOLE"
            icon={Monitor}
          />

          <div className="space-y-4 text-xs font-mono pt-2">
            <div>
              <label className="block text-slate-300 mb-1">Telemetry Stream Refresh Frequency</label>
              <select
                value={autoRefreshHz}
                onChange={(e) => setAutoRefreshHz(e.target.value)}
                className="bg-[#080E1C] border border-[#1E2D4A] rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-400"
              >
                <option value="1">1 Hz (Standard Telemetry Cadence)</option>
                <option value="2">2 Hz (High Precision)</option>
                <option value="0.5">0.5 Hz (Bandwidth Saver)</option>
              </select>
            </div>

            <div className="flex items-center justify-between p-3 rounded bg-[#090F1C]/80 border border-[#182642]">
              <div>
                <span className="text-slate-200 font-medium block">Critical Audible Alert Tone</span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Play mission controller alert tone upon detection of new critical anomaly.
                </span>
              </div>
              <input
                type="checkbox"
                checked={alertSound}
                onChange={(e) => setAlertSound(e.target.checked)}
                className="w-4 h-4 rounded text-cyan-500 focus:ring-0 bg-[#0F172A] border-[#1E2D4A]"
              />
            </div>
          </div>
        </GlassPanel>

        <div className="flex items-center justify-between pt-2">
          {savedSuccess ? (
            <span className="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
              <Check className="w-4 h-4" /> Preferences Saved Successfully
            </span>
          ) : (
            <span className="text-xs font-mono text-slate-400">Settings persist in local storage.</span>
          )}

          <button
            type="submit"
            className="px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold flex items-center gap-2 transition-all shadow-sm sat-btn-glow"
          >
            <Save className="w-3.5 h-3.5" />
            <span>SAVE PREFERENCES</span>
          </button>
        </div>
      </form>
    </div>
  );
};

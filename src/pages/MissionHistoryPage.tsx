import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/common/GlassPanel';
import { SectionHeader } from '../components/common/SectionHeader';
import { StatusBadge } from '../components/common/StatusBadge';
import { apiService } from '../services/api';
import type { MissionDataset } from '../types/mission';
import { LoadingState } from '../components/common/LoadingState';
import { History, Download, ArrowRight, Check } from 'lucide-react';

export const MissionHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [missions, setMissions] = useState<MissionDataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [exportedPassId, setExportedPassId] = useState<string | null>(null);

  useEffect(() => {
    apiService.getMissions().then((data) => {
      setMissions(data);
      setIsLoading(false);
    });
  }, []);

  const handleExport = (passId: string) => {
    setExportedPassId(passId);
    setTimeout(() => setExportedPassId(null), 2500);
  };

  if (isLoading) {
    return <LoadingState message="Loading Mission Archives..." submessage="Fetching historical pass logs" />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mission History & Telemetry Runs"
        subtitle="Review historical satellite passes, recorded anomalies, and past health evaluation archives."
        badge="GROUND PASS ARCHIVES"
      />

      <GlassPanel variant="accent" cornerAccents className="p-5">
        <SectionHeader
          title="RECORDED GROUND PASSES"
          subtitle="Comprehensive catalog of historical passes and detected anomaly events"
          badge={`${missions.length} PASS RECORDS`}
          icon={History}
        />

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#1E2D4A] text-slate-400">
                <th className="py-2.5 px-3">Pass ID</th>
                <th className="py-2.5 px-3">Spacecraft</th>
                <th className="py-2.5 px-3">Orbit Type</th>
                <th className="py-2.5 px-3">Epoch Start</th>
                <th className="py-2.5 px-3">Packets</th>
                <th className="py-2.5 px-3">Anomalies</th>
                <th className="py-2.5 px-3">Pass Status</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#182642]">
              {missions.map((m) => (
                <tr key={m.id} className="hover:bg-[#111C33]/80 transition-colors">
                  <td className="py-3 px-3 font-bold text-cyan-300">{m.id}</td>
                  <td className="py-3 px-3 text-slate-200">{m.satelliteDesignation}</td>
                  <td className="py-3 px-3 text-slate-400">{m.orbitType}</td>
                  <td className="py-3 px-3 text-slate-300">{m.epochStart}</td>
                  <td className="py-3 px-3 text-slate-300">{m.totalPackets.toLocaleString()}</td>
                  <td className="py-3 px-3">
                    {m.anomalyEventsFound > 0 ? (
                      <button
                        onClick={() => navigate('/anomalies')}
                        className="text-rose-400 font-bold bg-rose-950/60 hover:bg-rose-900/60 px-2 py-0.5 rounded border border-rose-500/30 flex items-center gap-1 transition-colors"
                        title="View flagged anomalies"
                      >
                        <span>{m.anomalyEventsFound} Flagged</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    ) : (
                      <span className="text-emerald-400 font-medium">0 Nominal</span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <StatusBadge status={m.status} size="sm" />
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => handleExport(m.id)}
                      className={`px-2.5 py-1 rounded text-[11px] font-mono flex items-center gap-1 ml-auto transition-all ${
                        exportedPassId === m.id
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50'
                          : 'bg-[#182642] hover:bg-[#20345B] text-slate-200 border border-[#2D4573]'
                      }`}
                      title="Export telemetry pass record"
                    >
                      {exportedPassId === m.id ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span>Exported</span>
                        </>
                      ) : (
                        <>
                          <Download className="w-3 h-3 text-cyan-400" />
                          <span>Export</span>
                        </>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>
    </div>
  );
};

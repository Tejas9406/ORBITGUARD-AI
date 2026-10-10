import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { SatelliteGlobe } from '../components/space/SatelliteGlobe';
import { SATELLITE_DIRECTORY } from '../data/satelliteDirectory';
import type { SatelliteMetadata } from '../types/satellite';
import {
  Search,
  Cpu,
} from 'lucide-react';

export const SatelliteIntelligencePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedSat, setSelectedSat] = useState<SatelliteMetadata>(SATELLITE_DIRECTORY[0]);

  // Filtering
  const filteredSatellites = SATELLITE_DIRECTORY.filter((sat) => {
    const matchesSearch =
      sat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sat.operator.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sat.operatingCountry.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sat.noradId.includes(searchTerm);
    const matchesStatus = statusFilter === 'ALL' || sat.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="SATELLITE CONSTELLATION & DIRECTORY"
        subtitle="Active orbital fleet surveillance, geographic ground track disambiguation, and subsystem telemetry links"
      />

      {/* Top 3D Earth Globe Intelligence Viewport */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SatelliteGlobe
            height={440}
            onSelectSatellite={(sat) => setSelectedSat(sat)}
          />
        </div>

        {/* Selected Satellite Telemetry & Metadata Inspector */}
        <div className="sat-panel p-5 rounded border border-[#162744] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#14233D] mb-4">
              <div>
                <span className="text-[10px] font-mono text-cyan-400 tracking-wider uppercase">
                  ACTIVE SELECTION &bull; {selectedSat.id}
                </span>
                <h3 className="font-display text-lg text-white font-semibold">{selectedSat.name}</h3>
              </div>
              <span
                className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                  selectedSat.status === 'CRITICAL'
                    ? 'bg-red-950 text-red-300 border border-red-800'
                    : selectedSat.status === 'WARNING'
                    ? 'bg-amber-950 text-amber-300 border border-amber-800'
                    : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                }`}
              >
                {selectedSat.status}
              </span>
            </div>

            {/* Geographical Disambiguation Banner */}
            <div className="p-3 rounded bg-[#070E1E] border border-cyan-500/20 mb-4 text-xs font-mono space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-400">Operating Country:</span>
                <span className="text-slate-100 font-bold">{selectedSat.operatingCountry}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Current Ground Track:</span>
                <span className="text-cyan-300 text-right">{selectedSat.currentSubpoint.geographicRegion}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Sub-Satellite Point:</span>
                <span className="text-slate-300">
                  {selectedSat.currentSubpoint.lat}° N, {selectedSat.currentSubpoint.lon}° E
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Data Stream Provenance:</span>
                <span
                  className={
                    selectedSat.dataSource === 'LIVE_BACKEND_STREAM'
                      ? 'text-emerald-400 font-semibold'
                      : 'text-amber-400'
                  }
                >
                  {selectedSat.dataSource === 'LIVE_BACKEND_STREAM'
                    ? 'LIVE FASTAPI STREAM'
                    : 'SIMULATED PROPAGATION'}
                </span>
              </div>
            </div>

            {/* Subsystem Status Matrix */}
            <h4 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Subsystem Health Matrix
            </h4>
            <div className="grid grid-cols-3 gap-2 mb-4 font-mono text-[11px]">
              {Object.entries(selectedSat.subsystems).map(([sub, stat]) => (
                <div
                  key={sub}
                  className="p-2 rounded bg-[#091326] border border-[#162744] flex flex-col justify-between"
                >
                  <span className="text-slate-400 uppercase text-[10px]">{sub}</span>
                  <span
                    className={`font-bold mt-1 text-[10px] ${
                      stat === 'CRITICAL'
                        ? 'text-red-400'
                        : stat === 'WARNING'
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }`}
                  >
                    {stat}
                  </span>
                </div>
              ))}
            </div>

            {/* Telemetry Channel Bindings */}
            <h4 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Assigned Telemetry Channels
            </h4>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {selectedSat.telemetryChannels.map((ch) => (
                <span
                  key={ch}
                  className="px-2 py-0.5 rounded bg-[#0C1A33] border border-cyan-500/30 text-cyan-200 font-mono text-[10px]"
                >
                  {ch}
                </span>
              ))}
            </div>
          </div>

          {/* Action CTAs */}
          <div className="pt-3 border-t border-[#14233D] flex items-center gap-3">
            <button
              onClick={() => navigate('/spacecraft')}
              className="flex-1 py-2.5 rounded bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-mono font-bold text-xs uppercase flex items-center justify-center gap-2 hover:brightness-110 shadow-[0_0_15px_rgba(0,229,255,0.3)] transition-all cursor-pointer sat-btn-glow"
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Inspect 3D Spacecraft</span>
            </button>
            <button
              onClick={() => navigate('/telemetry')}
              className="px-4 py-2.5 rounded bg-[#0B152A] border border-[#1E355B] hover:border-cyan-400 text-slate-200 font-mono text-xs uppercase transition-colors cursor-pointer"
            >
              Telemetry &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Searchable / Filterable Satellite Fleet Directory */}
      <div className="sat-panel p-6 rounded border border-[#162744]">
        <div className="flex flex-col sm:flex-row items-center justify-between pb-4 border-b border-[#14233D] gap-4 mb-6">
          <div>
            <h3 className="font-display text-xl text-white font-semibold">Spacecraft Registry Directory</h3>
            <p className="text-xs text-slate-400">
              Complete catalog of monitored operational and demonstration constellation units
            </p>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search satellite, operator, NORAD..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded bg-[#070D1C] border border-[#1E355B] text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-400"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="py-2 px-3 rounded bg-[#070D1C] border border-[#1E355B] text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-400 cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="NOMINAL">Nominal</option>
              <option value="WARNING">Warning</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>
        </div>

        {/* Directory Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#14233D] text-slate-400 uppercase text-[10px]">
                <th className="py-3 px-4">Spacecraft Name / ID</th>
                <th className="py-3 px-4">Operator</th>
                <th className="py-3 px-4">Operating Country</th>
                <th className="py-3 px-4">Current Subpoint</th>
                <th className="py-3 px-4">Orbit & Altitude</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#14233D]/60 text-slate-300">
              {filteredSatellites.map((sat) => (
                <tr
                  key={sat.id}
                  className={`hover:bg-[#0A162C]/50 transition-colors cursor-pointer ${
                    selectedSat.id === sat.id ? 'bg-[#0B1A36]/60 border-l-2 border-cyan-400' : ''
                  }`}
                  onClick={() => setSelectedSat(sat)}
                >
                  <td className="py-3.5 px-4 font-semibold text-slate-100">
                    <div className="flex items-center gap-2">
                      <span>{sat.name}</span>
                      <span className="text-[10px] text-cyan-400">({sat.noradId})</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">{sat.operator}</td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded bg-[#0A162C] border border-cyan-500/20 text-cyan-300 text-[11px]">
                      {sat.operatingCountry}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">{sat.currentSubpoint.geographicRegion}</td>
                  <td className="py-3.5 px-4">
                    {sat.altitudeKm} km &bull; {sat.orbitType}
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        sat.status === 'CRITICAL'
                          ? 'bg-red-950 text-red-300 border border-red-800'
                          : sat.status === 'WARNING'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}
                    >
                      {sat.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedSat(sat);
                        navigate('/spacecraft');
                      }}
                      className="px-2.5 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/30 text-[10px] uppercase font-semibold transition-colors"
                    >
                      Inspect Twin &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { SpacecraftModel } from '../components/space/SpacecraftModel';
import type { SubsystemKey } from '../components/space/SpacecraftModel';
import {
  Cpu,
  Zap,
  Thermometer,
  Compass,
  Radio,
  Eye,
  AlertTriangle,
  ArrowLeft,
  ShieldAlert,
} from 'lucide-react';

interface SubsystemInfo {
  name: string;
  fullName: string;
  status: 'NOMINAL' | 'WARNING' | 'CRITICAL';
  description: string;
  channels: { key: string; name: string; value: string; unit: string; status: 'NOMINAL' | 'WARNING' | 'CRITICAL'; range: string }[];
  anomalies: string[];
}

const SUBSYSTEM_METRICS: Record<SubsystemKey, SubsystemInfo> = {
  EPS: {
    name: 'EPS',
    fullName: 'Electrical Power System',
    status: 'WARNING',
    description: 'Soyuz dual silicon solar array wings, Apollo H2/O2 fuel cells (1/2/3), and joint docking interface power transfer.',
    channels: [
      { key: 'P-1', name: 'Soyuz Solar Wing Voltage', value: '27.8', unit: 'V', status: 'NOMINAL', range: '26.5 - 29.0 V' },
      { key: 'P-2', name: 'Apollo Fuel Cell Bus B Current', value: '31.4', unit: 'A', status: 'WARNING', range: '18.0 - 28.0 A' },
      { key: 'P-3', name: 'Docking Power Transfer Bus', value: '28.1', unit: 'V', status: 'NOMINAL', range: '27.0 - 29.5 V' },
    ],
    anomalies: ['P-2 Apollo Fuel Cell Bus B current excursion during docking tunnel seal heating'],
  },
  TCS: {
    name: 'TCS',
    fullName: 'Thermal Control System',
    status: 'CRITICAL',
    description: 'Apollo Service Module radiator freon loops, Command Module ablative heat shield, and Docking Module thermal blankets.',
    channels: [
      { key: 'T-1', name: 'Docking Hatch Seal Temp', value: '44.8', unit: '°C', status: 'CRITICAL', range: '10.0 - 32.0 °C' },
      { key: 'T-2', name: 'Apollo SM Radiator Freon Loop', value: '14.2', unit: '°C', status: 'NOMINAL', range: '5.0 - 22.0 °C' },
      { key: 'T-3', name: 'Soyuz Orbital Module Skin Temp', value: '-8.5', unit: '°C', status: 'NOMINAL', range: '-30 - +25 °C' },
    ],
    anomalies: ['T-1 Docking Module hatch thermal interface exceedance (+44.8°C exceeds 32.0°C limit)'],
  },
  AOCS: {
    name: 'AOCS',
    fullName: 'Attitude and Orbit Control System',
    status: 'NOMINAL',
    description: 'Apollo Service Module quad RCS thrusters, Soyuz gyro rates, and Androgynous Peripheral Attach System (APAS) alignment.',
    channels: [
      { key: 'A-1', name: 'Apollo Quad RCS Manifold Press', value: '182', unit: 'PSI', status: 'NOMINAL', range: '160 - 205 PSI' },
      { key: 'A-2', name: 'Soyuz Attitude Drift Rate', value: '0.008', unit: 'deg/s', status: 'NOMINAL', range: '< 0.03 deg/s' },
      { key: 'A-3', name: 'APAS Docking Boresight Error', value: '0.024', unit: 'deg', status: 'NOMINAL', range: '< 0.08 deg' },
    ],
    anomalies: [],
  },
  TTC: {
    name: 'TT&C',
    fullName: 'Telemetry, Tracking & Command',
    status: 'NOMINAL',
    description: 'Joint VHF voice/ranging transponder, S-band steerable dish antenna, and Houston-Moscow ground relay links.',
    channels: [
      { key: 'C-1', name: 'Joint VHF Ranging Margin', value: '+18.4', unit: 'dB', status: 'NOMINAL', range: '> 10.0 dB' },
      { key: 'C-2', name: 'Apollo S-Band High-Gain Carrier', value: '-78.5', unit: 'dBm', status: 'NOMINAL', range: '-95 - -60 dBm' },
      { key: 'C-3', name: 'Argon Telemetry Encoder Sync', value: '99.98', unit: '%', status: 'NOMINAL', range: '> 99.0 %' },
    ],
    anomalies: [],
  },
  OBC: {
    name: 'OBC',
    fullName: 'Guidance Computer & Instrumentation',
    status: 'NOMINAL',
    description: 'Apollo Guidance Computer (AGC - Block II), Soyuz Argon-16 sequencer, and Docking Module latching interlock controllers.',
    channels: [
      { key: 'E-1', name: 'AGC Core Memory Cycle Load', value: '38.4', unit: '%', status: 'NOMINAL', range: '< 70 %' },
      { key: 'E-2', name: 'Docking Latch Sequence State', value: 'LOCKED', unit: 'MODE', status: 'NOMINAL', range: 'READY / LOCKED' },
      { key: 'E-3', name: 'Inertial Subsystem Checksum', value: 'VALID', unit: '', status: 'NOMINAL', range: 'VALID' },
    ],
    anomalies: [],
  },
  SENSORS: {
    name: 'SENSORS',
    fullName: 'Docking & Environmental Sensors',
    status: 'WARNING',
    description: 'Docking target optical reticle cameras, cabin O2/N2 gas partial pressure monitors, and ionizing radiation dosimeters.',
    channels: [
      { key: 'S-1', name: 'Docking Target Optical Offset', value: '1.8', unit: 'mm', status: 'NOMINAL', range: '< 5.0 mm' },
      { key: 'S-2', name: 'Docking Module N2 Partial Press', value: '24.2', unit: 'kPa', status: 'WARNING', range: '18.0 - 22.0 kPa' },
      { key: 'S-3', name: 'Ionizing Radiation Dosimetry', value: '12.4', unit: 'mrad/h', status: 'NOMINAL', range: '< 25.0 mrad/h' },
    ],
    anomalies: ['S-2 Docking Module nitrogen equalisation pressure spike during hatch pressurisation'],
  },
};

export const SpacecraftDigitalTwinPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedSubsystem, setSelectedSubsystem] = useState<SubsystemKey>('TCS');

  const currentInfo = SUBSYSTEM_METRICS[selectedSubsystem];

  const getSubsystemIcon = (key: SubsystemKey) => {
    switch (key) {
      case 'EPS':
        return <Zap className="w-4 h-4" />;
      case 'TCS':
        return <Thermometer className="w-4 h-4" />;
      case 'AOCS':
        return <Compass className="w-4 h-4" />;
      case 'TTC':
        return <Radio className="w-4 h-4" />;
      case 'OBC':
        return <Cpu className="w-4 h-4" />;
      case 'SENSORS':
        return <Eye className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header with Navigation Link */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/satellites')}
            className="inline-flex items-center gap-1.5 text-xs font-mono text-cyan-400 hover:text-cyan-300 mb-2 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Earth Constellation</span>
          </button>
          <PageHeader
            title="3D SPACECRAFT DIGITAL TWIN"
            subtitle="CAD-grade interactive assembly inspection for Apollo-Soyuz (ASTP) Joint Orbital Docking Complex"
          />
        </div>

        {/* Spacecraft Identification Badge */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-1.5 rounded bg-[#091224] border border-cyan-500/40 text-xs font-mono">
            <span className="text-slate-400">TARGET: </span>
            <span className="text-white font-bold">APOLLO-SOYUZ (ASTP)</span>
            <span className="text-slate-500 mx-2">|</span>
            <span className="text-cyan-400">ORBITAL 225 KM</span>
          </div>
        </div>
      </div>

      {/* Subsystem Selector Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        {(Object.keys(SUBSYSTEM_METRICS) as SubsystemKey[]).map((key) => {
          const info = SUBSYSTEM_METRICS[key];
          const isSelected = selectedSubsystem === key;
          return (
            <button
              key={key}
              onClick={() => setSelectedSubsystem(key)}
              className={`px-4 py-2 rounded text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
                isSelected
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                  : 'bg-[#091326] border border-[#162744] text-slate-300 hover:border-cyan-400 hover:text-white'
              }`}
            >
              {getSubsystemIcon(key)}
              <span>{info.name}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  info.status === 'CRITICAL'
                    ? 'bg-red-400 animate-ping'
                    : info.status === 'WARNING'
                    ? 'bg-amber-400'
                    : 'bg-emerald-400'
                }`}
              />
            </button>
          );
        })}
      </div>

      {/* Main 3D Model & Telemetry Inspector Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: 3D Interactive Spacecraft */}
        <div className="lg:col-span-2">
          <SpacecraftModel
            height={520}
            selectedSubsystem={selectedSubsystem}
            onSelectSubsystem={(k) => setSelectedSubsystem(k)}
            activeAnomalySubsystem="TCS"
          />
        </div>

        {/* Right: Subsystem Telemetry Details */}
        <div className="sat-panel p-6 rounded border border-[#162744] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#14233D] mb-4">
              <div>
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                  SELECTED SUBASSEMBLY
                </span>
                <h3 className="font-display text-xl text-white font-bold">{currentInfo.fullName}</h3>
              </div>
              <span
                className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                  currentInfo.status === 'CRITICAL'
                    ? 'bg-red-950 text-red-300 border border-red-800'
                    : currentInfo.status === 'WARNING'
                    ? 'bg-amber-950 text-amber-300 border border-amber-800'
                    : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                }`}
              >
                {currentInfo.status}
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-6 font-mono">
              {currentInfo.description}
            </p>

            {/* Live Telemetry Channel Readouts */}
            <h4 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider mb-3">
              Monitored Telemetry Channels
            </h4>
            <div className="space-y-3 mb-6">
              {currentInfo.channels.map((ch) => (
                <div
                  key={ch.key}
                  className="p-3 rounded bg-[#070E1E] border border-[#14233D] flex items-center justify-between font-mono text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-bold">{ch.key}</span>
                      <span className="text-slate-200">{ch.name}</span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">Bounds: {ch.range}</div>
                  </div>
                  <div className="text-right">
                    <span
                      className={`font-bold text-sm ${
                        ch.status === 'CRITICAL'
                          ? 'text-red-400 font-mono'
                          : ch.status === 'WARNING'
                          ? 'text-amber-400 font-mono'
                          : 'text-emerald-400 font-mono'
                      }`}
                    >
                      {ch.value} {ch.unit}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Active Anomaly Warnings & Deep Link */}
            {currentInfo.anomalies.length > 0 && (
              <div className="p-3.5 rounded bg-red-950/40 border border-red-500/40 mb-6">
                <div className="flex items-center gap-2 text-red-300 text-xs font-mono font-bold mb-1.5">
                  <ShieldAlert className="w-4 h-4 text-red-400" />
                  <span>ACTIVE ANOMALY LINK DETECTED</span>
                </div>
                {currentInfo.anomalies.map((a, i) => (
                  <p key={i} className="text-xs font-mono text-red-200 leading-relaxed">
                    &bull; {a}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Action CTAs */}
          <div className="pt-4 border-t border-[#14233D] flex items-center gap-3">
            <button
              onClick={() => navigate('/anomalies')}
              className="flex-1 py-2.5 rounded bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-200 font-mono text-xs font-bold uppercase flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              <span>Investigate Anomaly</span>
            </button>
            <button
              onClick={() => navigate('/telemetry')}
              className="px-4 py-2.5 rounded bg-[#091326] border border-[#162744] hover:border-cyan-400 text-slate-200 font-mono text-xs uppercase transition-colors cursor-pointer"
            >
              Explorer &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LandingEarthScene } from '../components/landing/LandingEarthScene';
import {
  Shield,
  ArrowRight,
  Activity,
  AlertTriangle,
  Globe2,
  Cpu,
  Layers,
  ChevronDown,
  Sparkles,
  CheckCircle2,
  Radio,
  Eye,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedSatellite, setSelectedSatellite] = useState<string | null>(null);

  const handleEnterDashboard = () => {
    navigate('/dashboard');
  };

  const handleExploreSatellites = () => {
    navigate('/satellites');
  };

  const handleOpenSpacecraft = () => {
    navigate('/spacecraft');
  };

  const handleOpenVision = () => {
    navigate('/vision');
  };

  return (
    <div className="relative min-h-screen bg-[#030611] text-slate-100 overflow-x-hidden selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation Bar */}
      <header className="fixed top-0 left-0 right-0 z-50 h-20 px-6 lg:px-12 flex items-center justify-between border-b border-[#142340]/60 bg-[#030611]/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-400/50 flex items-center justify-center shadow-[0_0_15px_rgba(0,229,255,0.3)]">
            <Shield className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <span className="font-display text-xl tracking-wider text-white">
              SAT<span className="text-cyan-400">SHIELD</span>
            </span>
            <span className="hidden sm:inline-block ml-3 px-2 py-0.5 text-[10px] font-mono tracking-widest uppercase bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 rounded">
              v1.0 AEROSPACE PLATFORM
            </span>
          </div>
        </div>

        <nav className="flex items-center gap-3 sm:gap-6">
          <button
            onClick={() => {
              const el = document.getElementById('story-capabilities');
              el?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="hidden md:inline-flex text-xs font-mono tracking-wider text-slate-400 hover:text-cyan-300 transition-colors uppercase"
          >
            Capabilities
          </button>
          <button
            onClick={handleExploreSatellites}
            className="hidden md:inline-flex text-xs font-mono tracking-wider text-slate-400 hover:text-cyan-300 transition-colors uppercase"
          >
            Satellite Directory
          </button>
          <button
            onClick={handleOpenSpacecraft}
            className="hidden lg:inline-flex text-xs font-mono tracking-wider text-slate-400 hover:text-cyan-300 transition-colors uppercase"
          >
            3D Digital Twin
          </button>
          <button
            onClick={handleOpenVision}
            className="hidden lg:inline-flex text-xs font-mono tracking-wider text-slate-400 hover:text-cyan-300 transition-colors uppercase"
          >
            Computer Vision
          </button>

          {/* Primary Quick CTA */}
          <button
            id="enter-mission-control-btn-top"
            onClick={handleEnterDashboard}
            className="relative px-5 py-2.5 rounded bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-semibold text-xs tracking-wider uppercase flex items-center gap-2 hover:brightness-110 shadow-[0_0_20px_rgba(0,229,255,0.4)] transition-all cursor-pointer sat-btn-glow"
          >
            <span>Enter Mission Control</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="relative w-full h-screen min-h-[700px] flex items-center justify-between pt-20 px-6 lg:px-16 overflow-hidden">
        {/* 3D Earth Background & Interactive Canvas (Full crystal-clear opacity) */}
        <div className="absolute inset-0 z-0 opacity-100">
          <LandingEarthScene
            onSelectSatellite={(id) => {
              setSelectedSatellite(id);
            }}
          />
        </div>

        {/* Subtle Scrim for Left-Side Text Readability (Leaves Earth 100% luminous and unobstructed on the right) */}
        <div className="absolute inset-y-0 left-0 w-full md:w-[46%] max-w-2xl z-10 pointer-events-none bg-gradient-to-r from-[#030611]/90 via-[#030611]/45 to-transparent" />

        {/* Hero Content Left Panel */}
        <div className="relative z-20 max-w-2xl py-12 flex flex-col justify-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-mono tracking-wider uppercase mb-6 w-fit backdrop-blur-md">
            <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span>Telemetry Anomaly Detection & Spacecraft Digital Twin</span>
          </div>

          <h1 className="font-display text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight text-white mb-6 leading-none">
            SAT<span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-500">SHIELD</span>
          </h1>

          <p className="text-xl sm:text-2xl text-slate-200 font-light mb-4 tracking-normal leading-relaxed">
            Satellite Intelligence. <br className="hidden sm:inline" />
            <span className="text-cyan-400 font-medium">Anomalies Before They Escalate.</span>
          </p>

          <p className="text-sm sm:text-base text-slate-400 mb-8 max-w-xl leading-relaxed">
            Next-generation autonomous spacecraft health surveillance, multivariate anomaly scoring, and interactive 3D orbital digital twins designed for ISRO SPACE-03 operations.
          </p>

          <div className="flex flex-wrap items-center gap-4">
            <button
              id="hero-primary-cta"
              onClick={handleEnterDashboard}
              className="px-8 py-3.5 rounded bg-gradient-to-r from-cyan-400 via-cyan-500 to-blue-600 text-slate-950 font-bold text-sm tracking-wider uppercase flex items-center gap-3 hover:shadow-[0_0_30px_rgba(0,229,255,0.6)] transition-all cursor-pointer sat-btn-glow"
            >
              <span>Enter Mission Control</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={handleExploreSatellites}
              className="px-6 py-3.5 rounded bg-[#0A162C]/80 border border-cyan-500/40 text-slate-200 text-sm font-mono tracking-wider uppercase flex items-center gap-2 hover:border-cyan-400 hover:text-white transition-all backdrop-blur-md cursor-pointer"
            >
              <Globe2 className="w-4 h-4 text-cyan-400" />
              <span>Explore Earth & Constellation</span>
            </button>
          </div>

          {selectedSatellite && (
            <div className="mt-8 p-3.5 rounded bg-[#081224]/90 border border-cyan-400/40 backdrop-blur-md max-w-md animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                  <span className="text-xs font-mono text-cyan-200 font-bold uppercase">
                    Orbital Target: {selectedSatellite}
                  </span>
                </div>
                <button
                  onClick={() => navigate('/satellites')}
                  className="text-[11px] text-cyan-400 hover:underline font-mono"
                >
                  View Details &rarr;
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Scroll Indicator */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 pointer-events-none opacity-80">
          <span className="text-[10px] font-mono tracking-widest text-slate-400 uppercase">Scroll to explore</span>
          <ChevronDown className="w-4 h-4 text-cyan-400 animate-bounce" />
        </div>
      </section>

      {/* Storytelling Section 1: Constellation & Orbital Precision */}
      <section id="story-capabilities" className="relative py-24 px-6 lg:px-16 border-t border-[#142340] bg-[#040817]">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
            <div>
              <span className="text-xs font-mono tracking-widest text-cyan-400 uppercase">Phase 01 / Orbital Twin</span>
              <h2 className="font-display text-3xl sm:text-4xl text-white mt-2">
                Geospatial Earth & Spacecraft Constellation
              </h2>
            </div>
            <p className="text-sm text-slate-400 max-w-md">
              Real-time ground track projection, Keplerian orbital propagation, geographic sub-satellite point disambiguation, and ground station contact windows.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded sat-glass-card">
              <div className="w-10 h-10 rounded bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400 mb-4">
                <Globe2 className="w-5 h-5" />
              </div>
              <h3 className="font-display text-lg text-slate-100 mb-2">Multi-Layer Earth Digital Twin</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Toggle country boundaries, ground tracking stations, sensor footprints, and demonstration weather vector maps with clear data provenance labeling.
              </p>
            </div>

            <div className="p-6 rounded sat-glass-card">
              <div className="w-10 h-10 rounded bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400 mb-4">
                <Activity className="w-5 h-5" />
              </div>
              <h3 className="font-display text-lg text-slate-100 mb-2">Ground Track Disambiguation</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Strict distinction between the sovereign operating nation of the satellite and the transient geographic territory beneath its sub-satellite coordinates.
              </p>
            </div>

            <div className="p-6 rounded sat-glass-card">
              <div className="w-10 h-10 rounded bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400 mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="font-display text-lg text-slate-100 mb-2">Ground Station Telemetry Links</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Integrated visibility passes for ISRO NRSC Shadnagar, ISTRAC Bengaluru, and international polar Svalbard contact cones.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Storytelling Section 2: Telemetry Intelligence & Anomaly Engine */}
      <section className="relative py-24 px-6 lg:px-16 border-t border-[#142340] bg-[#02050E]">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
            <div>
              <span className="text-xs font-mono tracking-widest text-amber-400 uppercase">Phase 02 / Telemetry Intelligence</span>
              <h2 className="font-display text-3xl sm:text-4xl text-white mt-2">
                In-Process Anomaly Detection & ML Scoring
              </h2>
            </div>
            <p className="text-sm text-slate-400 max-w-md">
              Powered by ISRO SPACE-03 sensor channels, real-time dynamic threshold bounds, Isolation Forest, and rolling Z-score outlier classification.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-5 rounded sat-panel border border-[#16294A]">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">FastAPI Backend</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <h4 className="font-display text-base text-slate-100 mb-1">Live Telemetry Channels</h4>
              <p className="text-xs text-slate-400">
                Monitors power, thermal, attitude, and command streams with full decimation downsampling for 60fps Plotly visualization.
              </p>
            </div>

            <div className="p-5 rounded sat-panel border border-[#16294A]">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-amber-400 uppercase tracking-wider">In-Process ML</span>
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <h4 className="font-display text-base text-slate-100 mb-1">Isolation Forest</h4>
              <p className="text-xs text-slate-400">
                Detects multivariate telemetry shifts across non-linear channel clusters without relying on brittle subprocess scripts.
              </p>
            </div>

            <div className="p-5 rounded sat-panel border border-[#16294A]">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">NASA Benchmarks</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <h4 className="font-display text-base text-slate-100 mb-1">Telemanom Ground Truth</h4>
              <p className="text-xs text-slate-400">
                Expert-labeled anomaly windows with windowed Precision, Recall, and F1 score accuracy validations.
              </p>
            </div>

            <div className="p-5 rounded sat-panel border border-[#16294A]">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider">Replay Engine</span>
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <h4 className="font-display text-base text-slate-100 mb-1">Historical Scrubber</h4>
              <p className="text-xs text-slate-400">
                Step-by-step playback scrubber allowing mission operators to inspect anomaly evolutions across critical orbits.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Storytelling Section 3: Spacecraft Digital Twin & Vision */}
      <section className="relative py-24 px-6 lg:px-16 border-t border-[#142340] bg-[#04091A]">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-xs font-mono tracking-widest text-cyan-400 uppercase">Phase 03 / Engineering Twins</span>
              <h2 className="font-display text-3xl sm:text-4xl text-white mt-2 mb-4">
                Interactive Spacecraft Twin & Computer Vision
              </h2>
              <p className="text-sm text-slate-400 leading-relaxed mb-6">
                Inspect physical spacecraft subsystems in a dedicated 3D CAD environment. Select Solar Arrays (EPS), Thermal Radiators (TCS), Reaction Wheels (AOCS), and Antennas (TT&C) to drill down into synchronized real-time channel metrics.
              </p>

              <div className="flex flex-wrap gap-4">
                <button
                  onClick={handleOpenSpacecraft}
                  className="px-5 py-2.5 rounded bg-[#0A162C] border border-cyan-400/40 text-cyan-300 font-mono text-xs uppercase hover:bg-cyan-950/40 flex items-center gap-2 cursor-pointer"
                >
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <span>Launch 3D Spacecraft Twin</span>
                </button>
                <button
                  onClick={handleOpenVision}
                  className="px-5 py-2.5 rounded bg-[#0A162C] border border-cyan-400/40 text-cyan-300 font-mono text-xs uppercase hover:bg-cyan-950/40 flex items-center gap-2 cursor-pointer"
                >
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <span>Computer Vision Inspection</span>
                </button>
              </div>
            </div>

            <div className="p-8 rounded sat-glass-card border border-cyan-500/20">
              <div className="flex items-center justify-between pb-4 border-b border-[#1A2D4E] mb-6">
                <span className="text-xs font-mono font-bold text-slate-200 uppercase">SPACE-03 DIGITAL TWIN STATUS</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-red-950 text-red-300 border border-red-800">
                  CRITICAL: TCS EXCEEDANCE
                </span>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">EPS Solar Array Output</span>
                  <span className="font-mono text-emerald-400">28.4 V / NOMINAL</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">TCS Battery Thermocouple</span>
                  <span className="font-mono text-red-400 font-bold">+48.2 °C / CRITICAL</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">AOCS Reaction Wheel Speed</span>
                  <span className="font-mono text-emerald-400">3,420 RPM / NOMINAL</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">TT&C Downlink Margin</span>
                  <span className="font-mono text-cyan-400">+14.2 dB / LOCKED</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final Launch CTA Section */}
      <section className="relative py-28 px-6 lg:px-16 border-t border-[#142340] bg-gradient-to-b from-[#030611] to-[#01030A] text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-3xl sm:text-5xl text-white mb-6">
            Ready for Operational Deployment?
          </h2>
          <p className="text-sm sm:text-base text-slate-400 mb-8 max-w-xl mx-auto leading-relaxed">
            Enter the central SatShield Mission Control console to inspect live channels, triage active anomalies, and review mission telemetry.
          </p>

          <button
            id="launch-mission-control-btn-bottom"
            onClick={handleEnterDashboard}
            className="px-10 py-4 rounded-lg bg-gradient-to-r from-cyan-400 via-cyan-500 to-blue-600 text-slate-950 font-bold text-sm tracking-wider uppercase inline-flex items-center gap-3 hover:shadow-[0_0_35px_rgba(0,229,255,0.7)] transition-all cursor-pointer sat-btn-glow"
          >
            <span>Launch Mission Control Console</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-[#101D34] bg-[#02040A] text-center text-xs text-slate-500 font-mono">
        <div className="flex flex-col sm:flex-row items-center justify-between max-w-7xl mx-auto gap-4">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-semibold">SATSHIELD</span>
            <span>&bull;</span>
            <span>ISRO SPACE-03 AEROSPACE INTELLIGENCE</span>
          </div>
          <div>All Telemetry & Anomaly Processing Executed in Pure Frontend Environment</div>
        </div>
      </footer>
    </div>
  );
};

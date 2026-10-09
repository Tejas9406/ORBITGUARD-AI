import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/common/GlassPanel';
import { SectionHeader } from '../components/common/SectionHeader';
import { ReplayTimelineChart } from '../components/charts/ReplayTimelineChart';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { useReplay } from '../hooks/useReplay';
import type { PlaybackSpeed } from '../hooks/useReplay';
import {
  Play,
  Pause,
  RotateCcw,
  StepBack,
  StepForward,
  Activity,
  Cpu,
  Layers,
  MapPin,
  HeartPulse,
  AlertOctagon,
  Radio,
  Clock,
  Sparkles,
  Satellite,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';

export const TelemetryReplayPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentFrame,
    currentFrameIndex,
    totalFrames,
    isPlaying,
    speed,
    framesHistory,
    play,
    pause,
    restart,
    seek,
    changeSpeed,
    stepForward,
    stepBackward,
  } = useReplay();

  // SATSHIELD Core Pipeline Stages
  const pipelineStages = [
    { key: 'STREAM_INGEST', label: 'Telemetry Ingest', icon: Radio },
    { key: 'AI_DETECTION', label: 'AI Detection', icon: Cpu },
    { key: 'SCORING', label: 'Anomaly Scoring', icon: Activity },
    { key: 'ATTRIBUTION', label: 'Channel Attribution', icon: Layers },
    { key: 'LOCALIZATION', label: 'Subsystem Localization', icon: MapPin },
    { key: 'HEALTH_UPDATE', label: 'Health Update', icon: HeartPulse },
    { key: 'ALERT_ACTIVE', label: 'Operator Alert', icon: AlertOctagon },
  ];

  const currentStageIndex = pipelineStages.findIndex((s) => s.key === currentFrame.pipelineStage);

  // Status computation for satellite
  const isCritical = currentFrame.anomalyScore > 0.7;
  const isWarning = currentFrame.anomalyScore > 0.4 && !isCritical;
  const statusLabel = isCritical ? 'CRITICAL ANOMALY DETECTED' : isWarning ? 'TELEMETRY DRIFT WARNING' : 'NOMINAL FLIGHT OPERATIONS';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Telemetry Replay & Pipeline Simulator"
        subtitle="Step through historical flight streams to witness real-time multi-channel anomaly detection, isolation forest scoring, and automated operator alerts."
        badge="SIMULATED FLIGHT PASS #0924"
      />

      {/* Top Banner: Real-time Spacecraft Status Badge */}
      <GlassPanel
        variant={isCritical ? 'danger' : isWarning ? 'warning' : 'accent'}
        cornerAccents
        className="p-4"
      >
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded border ${
              isCritical
                ? 'bg-rose-950/80 border-rose-500 text-rose-300 animate-pulse'
                : isWarning
                ? 'bg-amber-950/80 border-amber-500 text-amber-300'
                : 'bg-cyan-950/80 border-cyan-500/50 text-cyan-300'
            }`}>
              {isCritical ? <ShieldAlert className="w-5 h-5" /> : isWarning ? <AlertTriangle className="w-5 h-5" /> : <Satellite className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-wider uppercase text-slate-400">
                  SATSHIELD-OBS-1 Spacecraft State
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  isCritical
                    ? 'bg-rose-950 text-rose-300 border-rose-500/50'
                    : isWarning
                    ? 'bg-amber-950 text-amber-300 border-amber-500/50'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-500/50'
                }`}>
                  {statusLabel}
                </span>
              </div>
              <p className="text-xs text-slate-300 font-mono mt-0.5">
                {isCritical
                  ? `Active Fault: Solar Array Bus Sag (-4.2V) & Secondary Battery Excursion. Pipeline Stage: ${pipelineStages[currentStageIndex]?.label || 'Alert Trigger'}`
                  : isWarning
                  ? 'Minor telemetry deviation identified. Statistical and Isolation Forest models updating belief distribution.'
                  : 'Telemetry streams steady within 3-sigma confidence bounds across EPS, TCS, AOCS, and TT&C.'}
              </p>
            </div>
          </div>

          {isCritical && currentFrame.hasActiveAnomaly && (
            <button
              onClick={() => navigate(`/anomalies?id=${currentFrame.activeAnomalyId || 'ANM-0047'}`)}
              className="px-3.5 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-mono text-xs font-bold flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(239,68,68,0.4)] whitespace-nowrap"
            >
              <span>INSPECT AI EXPLANATION</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </GlassPanel>

      {/* Replay Controls & Timeline Scrubber Card */}
      <GlassPanel variant="elevated" cornerAccents className="p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Playback action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={restart}
              className="p-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              title="Restart replay from beginning"
              aria-label="Restart replay"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            <button
              onClick={stepBackward}
              disabled={currentFrameIndex === 0}
              className="p-2 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 border border-slate-700 transition-colors"
              title="Step backward one frame"
              aria-label="Step backward"
            >
              <StepBack className="w-4 h-4" />
            </button>

            {isPlaying ? (
              <button
                onClick={pause}
                className="px-4 py-2 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-mono font-bold flex items-center gap-2 transition-colors shadow-md"
                aria-label="Pause playback"
              >
                <Pause className="w-4 h-4" />
                <span>PAUSE</span>
              </button>
            ) : (
              <button
                onClick={play}
                className="px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono font-bold flex items-center gap-2 transition-colors shadow-md"
                aria-label="Start playback"
              >
                <Play className="w-4 h-4" />
                <span>PLAY REPLAY</span>
              </button>
            )}

            <button
              onClick={stepForward}
              disabled={currentFrameIndex === totalFrames - 1}
              className="p-2 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 border border-slate-700 transition-colors"
              title="Step forward one frame"
              aria-label="Step forward"
            >
              <StepForward className="w-4 h-4" />
            </button>

            {/* Speed selection */}
            <div className="flex items-center gap-1 bg-[#090F1C] p-1 rounded border border-[#1E2D4A] ml-2">
              {([1, 2, 5] as PlaybackSpeed[]).map((sp) => (
                <button
                  key={sp}
                  onClick={() => changeSpeed(sp)}
                  className={`px-2 py-0.5 text-xs font-mono rounded transition-colors ${
                    speed === sp
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sp}x
                </button>
              ))}
            </div>
          </div>

          {/* Mission Time Readout */}
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-slate-300 bg-[#090F1C] px-3 py-1.5 rounded border border-[#1E2D4A]">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>Mission Time: <b className="text-cyan-300">{currentFrame.missionTime}</b></span>
            </div>
            <div className="text-slate-400">
              Frame: <span className="text-slate-200">{currentFrameIndex + 1} / {totalFrames}</span>
            </div>
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="space-y-1.5 pt-2">
          <input
            type="range"
            min={0}
            max={totalFrames - 1}
            value={currentFrameIndex}
            onChange={(e) => seek(parseInt(e.target.value, 10))}
            className="w-full accent-cyan-400 cursor-pointer h-2 bg-[#090F1C] rounded-lg border border-[#1E2D4A]"
            aria-label="Timeline scrubber"
          />

          <div className="flex justify-between text-[10px] font-mono text-slate-400">
            <span>T+04:45:15 (Nominal Baseline)</span>
            <span className="text-amber-400">T+04:49:30 (Drift Detected)</span>
            <span className="text-rose-400 font-bold">T+04:52:15 (Critical Alert Threshold)</span>
          </div>
        </div>
      </GlassPanel>

      {/* SATSHIELD Pipeline Flow Visualization (DETECT -> EXPLAIN -> LOCALIZE -> PRIORITIZE -> ACT) */}
      <GlassPanel variant="default" className="p-5">
        <SectionHeader
          title="AUTOMATED TELEMETRY PIPELINE STAGES"
          subtitle="Real-time multi-stage inference execution synchronized with playback frame"
          badge={`STAGE ${currentStageIndex + 1} / 7: ${pipelineStages[currentStageIndex]?.label || 'INGEST'}`}
          icon={Sparkles}
        />

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 mt-4">
          {pipelineStages.map((stage, idx) => {
            const Icon = stage.icon;
            const isCompleted = idx < currentStageIndex;
            const isCurrent = idx === currentStageIndex;

            let stageStyle = 'bg-[#090F1C]/80 border-[#182642] text-slate-400';
            if (isCurrent) {
              stageStyle = 'bg-cyan-950/80 border-cyan-400 text-cyan-200 shadow-[0_0_12px_rgba(0,229,255,0.35)] font-bold';
            } else if (isCompleted) {
              stageStyle = 'bg-[#0F1E36]/90 border-cyan-500/30 text-cyan-400';
            }

            return (
              <div
                key={stage.key}
                className={`p-2.5 rounded border flex flex-col items-center text-center transition-all duration-200 ${stageStyle}`}
              >
                <div className={`p-1.5 rounded-full mb-1.5 ${isCurrent ? 'bg-cyan-500 text-slate-900 animate-pulse' : isCompleted ? 'bg-cyan-950 text-cyan-300' : 'bg-slate-800'}`}>
                  {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5 text-cyan-300" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <span className="text-[10px] font-mono uppercase tracking-tight">{stage.label}</span>
                <span className="text-[9px] font-mono text-slate-400 mt-0.5">Step 0{idx + 1}</span>
              </div>
            );
          })}
        </div>
      </GlassPanel>

      {/* Replay Plotly Chart & Dynamic Telemetry State Readouts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 8 Cols: Replay Plotly Chart */}
        <section aria-label="Replay Telemetry Chart" className="lg:col-span-8">
          <ReplayTimelineChart
            framesHistory={framesHistory}
            currentFrame={currentFrame}
            height={380}
          />
        </section>

        {/* Right 4 Cols: Dynamic Replay Telemetry Values */}
        <GlassPanel variant="elevated" cornerAccents className="lg:col-span-4 p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A]/60">
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-200">
              Live Replay Telemetry State
            </h3>
            <span className="text-xs font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
              {currentFrame.timestamp}
            </span>
          </div>

          <div className="space-y-3 text-xs font-mono">
            {/* Primary Affected Channel Voltage */}
            <div className={`p-3 rounded border transition-colors ${
              currentFrame.solarArrayVoltage < 26.5
                ? 'bg-rose-950/40 border-rose-500/50 text-rose-300'
                : 'bg-[#090F1C] border-[#182642] text-slate-300'
            }`}>
              <div className="flex items-center justify-between">
                <span>Solar Array Bus (Ch_04):</span>
                <span className="text-base font-bold">{currentFrame.solarArrayVoltage} V</span>
              </div>
              <span className="text-[10px] text-slate-400">Operating limit: &gt; 26.5 V</span>
            </div>

            {/* Battery Temperature */}
            <div className={`p-3 rounded border transition-colors ${
              currentFrame.batteryTemperature > 30.0
                ? 'bg-amber-950/40 border-amber-500/50 text-amber-300'
                : 'bg-[#090F1C] border-[#182642] text-slate-300'
            }`}>
              <div className="flex items-center justify-between">
                <span>Battery Temp (Ch_12):</span>
                <span className="text-base font-bold">{currentFrame.batteryTemperature} °C</span>
              </div>
              <span className="text-[10px] text-slate-400">Max limit: 30.0 °C</span>
            </div>

            {/* AI Anomaly Score */}
            <div className="p-3 rounded bg-[#090F1C] border border-[#182642]">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">AI Anomaly Score:</span>
                <span className={`text-base font-bold ${
                  currentFrame.anomalyScore > 0.7 ? 'text-rose-400' : currentFrame.anomalyScore > 0.4 ? 'text-amber-400' : 'text-emerald-400'
                }`}>
                  {currentFrame.anomalyScore}
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-200 ${
                    currentFrame.anomalyScore > 0.7 ? 'bg-rose-500' : currentFrame.anomalyScore > 0.4 ? 'bg-amber-500' : 'bg-emerald-400'
                  }`}
                  style={{ width: `${currentFrame.anomalyScore * 100}%` }}
                />
              </div>
            </div>

            {/* System Health Score */}
            <div className="p-3 rounded bg-[#090F1C] border border-[#182642] flex items-center justify-between">
              <span className="text-slate-400">Health Index:</span>
              <span className={`text-base font-bold ${
                currentFrame.healthScore < 75 ? 'text-rose-400' : currentFrame.healthScore < 85 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {currentFrame.healthScore} / 100
              </span>
            </div>

            {/* Active Alert Indicator */}
            {currentFrame.hasActiveAnomaly ? (
              <div className="p-3 rounded bg-rose-950/60 border border-rose-500/60 text-xs font-mono text-rose-300 space-y-1">
                <div className="flex items-center justify-between font-bold">
                  <span>ACTIVE ALERT: {currentFrame.activeAnomalyId}</span>
                  <SeverityBadge severity={currentFrame.activeSeverity || 'CRITICAL'} size="sm" />
                </div>
                <p className="text-[11px] text-rose-200">
                  Subsystem: EPS • Affected: {currentFrame.affectedChannel}
                </p>
              </div>
            ) : (
              <div className="p-3 rounded bg-emerald-950/40 border border-emerald-500/30 text-xs font-mono text-emerald-400 text-center">
                All telemetry channels within nominal bounds.
              </div>
            )}
          </div>
        </GlassPanel>
      </div>
    </div>
  );
};

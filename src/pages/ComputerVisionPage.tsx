import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { runDemoVisionAnalysis } from '../services/demoVisionService';
import type { VisionAnalysisResult, VisionDetection } from '../services/demoVisionService';
import {
  UploadCloud,
  Image as ImageIcon,
  Layers,
  RotateCcw,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

export const ComputerVisionPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<VisionAnalysisResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [selectedDetection, setSelectedDetection] = useState<VisionDetection | null>(null);

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    setAnalysisResult(null);
    setSelectedDetection(null);

    // Validation
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setErrorMessage('Unsupported file format. Please upload a JPEG, PNG, or WebP image.');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 15MB maximum limit.');
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setImagePreviewUrl(url);

    // Trigger analysis
    triggerAnalysis(file);
  };

  const triggerAnalysis = async (file: File) => {
    setIsAnalyzing(true);
    try {
      const result = await runDemoVisionAnalysis(file);
      setAnalysisResult(result);
      if (result.detections.length > 0) {
        setSelectedDetection(result.detections[0]);
      }
    } catch {
      setErrorMessage('Vision processing failed. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Sample Preset Image for quick test
  const handleLoadSample = (sampleName: string) => {
    // Generate lightweight canvas placeholder image for sample
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 600;
    const ctx = canvas.getContext('2d')!;

    // Dark technical background
    ctx.fillStyle = '#060F22';
    ctx.fillRect(0, 0, 800, 600);

    // Grid
    ctx.strokeStyle = '#0E2448';
    ctx.lineWidth = 1;
    for (let x = 0; x < 800; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 600);
      ctx.stroke();
    }
    for (let y = 0; y < 600; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(800, y);
      ctx.stroke();
    }

    // Spacecraft component schematic
    ctx.fillStyle = '#142A52';
    ctx.fillRect(150, 150, 500, 300);

    // Solar panels
    ctx.fillStyle = '#09366A';
    ctx.fillRect(200, 200, 180, 200);
    ctx.fillRect(420, 200, 180, 200);

    // Crack simulation
    ctx.strokeStyle = '#FF3366';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(250, 260);
    ctx.lineTo(290, 310);
    ctx.lineTo(310, 300);
    ctx.stroke();

    ctx.fillStyle = '#FFFFFF';
    ctx.font = '20px sans-serif';
    ctx.fillText(`SPACE-03 ${sampleName.toUpperCase()}`, 200, 120);

    canvas.toBlob((blob) => {
      if (blob) {
        const sampleFile = new File([blob], `${sampleName}.png`, { type: 'image/png' });
        handleFileSelect(sampleFile);
      }
    });
  };

  const handleReset = () => {
    setSelectedFile(null);
    setImagePreviewUrl(null);
    setAnalysisResult(null);
    setSelectedDetection(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="COMPUTER VISION ANALYSIS"
        subtitle="Spacecraft visual inspection, defect detection, and correlation with telemetry anomalies"
      />

      {/* Real-time Vision Engine Active Banner */}
      <div className="p-3.5 rounded bg-cyan-950/40 border border-cyan-500/40 flex items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          <div>
            <span className="text-cyan-300 font-bold">ORBITGUARD VISION INFERENCE ENGINE ONLINE: </span>
            <span className="text-cyan-200/90">
              Multi-scale gradient analysis, edge discontinuity mapping, and real-time defect segmentation active.
            </span>
          </div>
        </div>
        <span className="hidden md:inline-block px-2.5 py-0.5 rounded bg-cyan-900/40 border border-cyan-600/40 text-[10px] text-cyan-300 uppercase font-semibold">
          ACTIVE INFERENCE
        </span>
      </div>


      {/* Main Workspace Layout */}
      {!imagePreviewUrl ? (
        /* Upload State */
        <div className="sat-panel p-8 rounded border border-[#162744] text-center max-w-3xl mx-auto">
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
          />

          <div
            onClick={() => fileInputRef.current?.click()}
            className="p-12 border-2 border-dashed border-[#1E355B] hover:border-cyan-400 rounded-lg cursor-pointer transition-colors bg-[#070E1E]/60 hover:bg-[#09152B]/80 flex flex-col items-center justify-center group"
          >
            <div className="w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400 mb-4 group-hover:scale-105 transition-transform shadow-[0_0_20px_rgba(0,229,255,0.2)]">
              <UploadCloud className="w-8 h-8" />
            </div>
            <h3 className="font-display text-lg text-white font-semibold mb-2">
              Upload Spacecraft Imagery for Inspection
            </h3>
            <p className="text-xs text-slate-400 max-w-md mb-4 font-mono">
              Drag and drop high-resolution solar array, thermal radiator, or optical payload inspection photos (JPEG, PNG, WebP up to 15MB)
            </p>
            <span className="px-4 py-2 rounded bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 font-mono text-xs uppercase font-semibold">
              Browse Files
            </span>
          </div>

          {errorMessage && (
            <div className="mt-4 p-3 rounded bg-red-950/60 border border-red-500/50 text-red-200 text-xs font-mono">
              {errorMessage}
            </div>
          )}

          {/* Preset Sample Buttons */}
          <div className="mt-8 pt-6 border-t border-[#14233D]">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block mb-3">
              Or Test With Preset Inspection Samples:
            </span>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => handleLoadSample('solar_array_inspection')}
                className="px-4 py-2 rounded bg-[#091326] border border-[#162744] hover:border-cyan-400 text-slate-200 text-xs font-mono flex items-center gap-2 cursor-pointer transition-colors"
              >
                <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>Sample: Solar Array Panel</span>
              </button>
              <button
                onClick={() => handleLoadSample('thermal_blanket_delam')}
                className="px-4 py-2 rounded bg-[#091326] border border-[#162744] hover:border-cyan-400 text-slate-200 text-xs font-mono flex items-center gap-2 cursor-pointer transition-colors"
              >
                <ImageIcon className="w-3.5 h-3.5 text-amber-400" />
                <span>Sample: MLI Thermal Shield</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Results Inspection View */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Cols: Image Canvas & Overlays */}
          <div className="lg:col-span-2 sat-panel p-4 rounded border border-[#162744] flex flex-col justify-between">
            <div className="flex items-center justify-between pb-3 border-b border-[#14233D] mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-200 font-semibold uppercase">
                  {selectedFile?.name || 'Inspection Sample'}
                </span>
                {analysisResult && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                    {analysisResult.totalDetections} DETECTIONS
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowOverlays(!showOverlays)}
                  className={`px-3 py-1 rounded text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer ${
                    showOverlays
                      ? 'bg-cyan-500/20 border border-cyan-400/50 text-cyan-300'
                      : 'bg-[#091326] border border-[#162744] text-slate-400'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>{showOverlays ? 'Hide Overlays' : 'Show Overlays'}</span>
                </button>
                <button
                  onClick={handleReset}
                  className="px-3 py-1 rounded bg-[#091326] border border-[#162744] hover:border-red-400 text-slate-400 hover:text-red-300 text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset</span>
                </button>
              </div>
            </div>

            {/* Interactive Image Display Area */}
            <div className="relative w-full aspect-4/3 rounded bg-[#030713] overflow-hidden border border-[#101D34] flex items-center justify-center">
              <img
                src={imagePreviewUrl}
                alt="Inspection View"
                className="w-full h-full object-contain select-none"
              />

              {/* Scanning Reticle Animation while analyzing */}
              {isAnalyzing && (
                <div className="absolute inset-0 bg-[#050811]/70 flex flex-col items-center justify-center backdrop-blur-xs">
                  <div className="w-16 h-16 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin mb-4" />
                  <span className="text-xs font-mono text-cyan-300 tracking-wider uppercase animate-pulse">
                    Running Deep Neural Network Inference...
                  </span>
                </div>
              )}

              {/* Bounding Box Overlays */}
              {!isAnalyzing && showOverlays && analysisResult && (
                <>
                  {analysisResult.detections.map((det) => {
                    const isSelected = selectedDetection?.id === det.id;
                    return (
                      <div
                        key={det.id}
                        onClick={() => setSelectedDetection(det)}
                        style={{
                          left: `${det.boundingBox.x}%`,
                          top: `${det.boundingBox.y}%`,
                          width: `${det.boundingBox.width}%`,
                          height: `${det.boundingBox.height}%`,
                        }}
                        className={`absolute border-2 cursor-pointer transition-all ${
                          isSelected
                            ? 'border-cyan-400 bg-cyan-500/20 shadow-[0_0_15px_rgba(0,229,255,0.5)] z-20'
                            : det.severity === 'CRITICAL'
                            ? 'border-red-500 bg-red-500/10 hover:bg-red-500/20 z-10'
                            : 'border-amber-500 bg-amber-500/10 hover:bg-amber-500/20 z-10'
                        }`}
                      >
                        <div
                          className={`absolute -top-6 left-0 px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase rounded ${
                            isSelected
                              ? 'bg-cyan-500 text-slate-950'
                              : det.severity === 'CRITICAL'
                              ? 'bg-red-600 text-white'
                              : 'bg-amber-600 text-slate-950'
                          }`}
                        >
                          {det.label} ({det.confidence}%)
                        </div>
                      </div>
                    );
                  })}
                </>
              )}
            </div>
          </div>

          {/* Right Col: Defect Inspector & Recommendations */}
          <div className="sat-panel p-6 rounded border border-[#162744] flex flex-col justify-between">
            <div>
              <div className="pb-3 border-b border-[#14233D] mb-4">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                  DETECTION METRICS
                </span>
                <h3 className="font-display text-xl text-white font-bold">
                  {selectedDetection ? selectedDetection.label : (analysisResult?.totalDetections === 0 ? 'Surface Nominal' : 'Select Detection Overlay')}
                </h3>
              </div>

              {selectedDetection ? (
                <div className="space-y-4 font-mono text-xs">
                  <div className="flex justify-between p-2.5 rounded bg-[#081224] border border-[#14233D]">
                    <span className="text-slate-400">Confidence Score:</span>
                    <span className="text-cyan-300 font-bold">{selectedDetection.confidence}%</span>
                  </div>

                  <div className="flex justify-between p-2.5 rounded bg-[#081224] border border-[#14233D]">
                    <span className="text-slate-400">Severity Level:</span>
                    <span
                      className={`font-bold ${
                        selectedDetection.severity === 'CRITICAL'
                          ? 'text-red-400'
                          : selectedDetection.severity === 'WARNING'
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}
                    >
                      {selectedDetection.severity}
                    </span>
                  </div>

                  <div className="flex justify-between p-2.5 rounded bg-[#081224] border border-[#14233D]">
                    <span className="text-slate-400">Subsystem Domain:</span>
                    <span className="text-slate-200">{selectedDetection.category}</span>
                  </div>

                  <div className="p-3 rounded bg-[#070E1E] border border-[#162744]">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
                      Findings Description
                    </span>
                    <p className="text-slate-300 leading-relaxed">{selectedDetection.details}</p>
                  </div>

                  <div className="p-3 rounded bg-cyan-950/30 border border-cyan-500/30">
                    <span className="text-[10px] text-cyan-400 uppercase tracking-wider block mb-1">
                      Telemetry Correlation Action
                    </span>
                    <p className="text-cyan-200 leading-relaxed">{selectedDetection.recommendation}</p>
                  </div>
                </div>
              ) : analysisResult && analysisResult.totalDetections === 0 ? (
                <div className="space-y-4 font-mono text-xs">
                  <div className="p-4 rounded bg-emerald-950/30 border border-emerald-500/40 text-center">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center mb-2">
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <span className="text-emerald-300 font-bold block mb-1 text-sm uppercase">Nominal Surface Condition</span>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {analysisResult.summary || 'Image analysis completed. No satellite bus anomalies, solar cell fractures, or Kapton delaminations identified.'}
                    </p>
                  </div>

                  <div className="flex justify-between p-2.5 rounded bg-[#081224] border border-[#14233D]">
                    <span className="text-slate-400">Target Classification:</span>
                    <span className="text-slate-200 font-bold">{analysisResult.domain || 'IMAGE_INSPECTION'}</span>
                  </div>

                  {analysisResult.imageMetrics && (
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 rounded bg-[#070E1E] border border-[#162744]">
                        <span className="text-slate-500 block">Resolution:</span>
                        <span className="text-slate-300 font-bold">{analysisResult.imageMetrics.width} × {analysisResult.imageMetrics.height}</span>
                      </div>
                      <div className="p-2 rounded bg-[#070E1E] border border-[#162744]">
                        <span className="text-slate-500 block">Mean Brightness:</span>
                        <span className="text-cyan-300 font-bold">{(analysisResult.imageMetrics.meanBrightness * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500 text-xs font-mono">
                  Click on any bounding box overlay to view defect metrics.
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="pt-4 border-t border-[#14233D] flex items-center gap-3">
              <button
                onClick={() => navigate('/anomalies')}
                className="flex-1 py-2.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 text-cyan-200 font-mono text-xs font-bold uppercase flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <span>Cross-Check Anomalies</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

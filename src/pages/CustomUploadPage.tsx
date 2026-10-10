import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { Upload, FileText, AlertTriangle, Loader2, CheckCircle2, ArrowRight, Activity, Sliders, Database } from 'lucide-react';
import { apiService } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';

export const CustomUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedResult, setUploadedResult] = useState<any | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setUploadedResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const dataset = await apiService.upload(file);
      await apiService.setDataset(dataset.id); // set as global active working dataset
      
      // Run analysis on first detected channel
      const primaryChannel = dataset.channels?.[0] || 'sensor_channel_4';
      try {
        await apiService.runAnalysis(primaryChannel);
      } catch (analysisErr) {
        console.warn('Initial pipeline pass warning:', analysisErr);
      }

      setUploadedResult(dataset);
    } catch (err: any) {
      setError(err.message || 'Dataset upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Custom Telemetry Ingestion"
        subtitle="Upload raw multi-sensor telemetry (CSV) to process through the OrbitGuard anomaly detection pipeline."
        badge="REAL-WORLD ANALYSIS"
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload Box */}
        <div className={`sat-panel p-6 ${uploadedResult ? 'lg:col-span-5' : 'lg:col-span-8 lg:col-start-3'} transition-all`}>
          <h3 className="font-mono text-sm font-semibold text-slate-200 uppercase mb-4 border-b border-[#1E2D4A]/60 pb-2 flex items-center gap-2">
            <Upload className="w-4 h-4 text-cyan-400" />
            Ingest Mission Data
          </h3>

          <div className="border-2 border-dashed border-[#1E2D4A] hover:border-cyan-500/50 rounded-lg p-8 text-center transition-colors">
            <input
              type="file"
              id="file-upload"
              accept=".csv"
              className="hidden"
              onChange={handleFileChange}
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer flex flex-col items-center justify-center space-y-3"
            >
              <div className="p-3 bg-[#0A1224] rounded-full text-cyan-400 border border-[#1E2D4A]">
                <FileText className="w-8 h-8" />
              </div>
              <div className="text-sm text-slate-300 font-mono">
                {file ? (
                  <span className="text-emerald-400 font-bold">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
                ) : (
                  <span>Click to select or drag and drop a CSV file</span>
                )}
              </div>
              <p className="text-xs text-slate-500 font-mono">Format: Timestamp, Feature1, Feature2, ...</p>
            </label>
          </div>

          <div className="mt-6 flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400">
              {file ? 'Ready to process' : 'No file selected'}
            </span>
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className={`px-4 py-2 font-mono text-xs font-bold rounded flex items-center gap-2 transition-all cursor-pointer ${
                !file || uploading
                  ? 'bg-[#101D36] text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-[0_0_12px_rgba(0,229,255,0.4)]'
              }`}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Ingesting & Analyzing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" /> Ingest & Set Active Dataset
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-6 p-4 rounded bg-rose-950/40 border border-rose-500/50 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <div className="text-sm font-mono text-rose-300">
                <span className="font-bold block mb-1">Execution Failed</span>
                {error}
              </div>
            </div>
          )}
        </div>

        {/* Statistical Inspection of Uploaded Telemetry */}
        {uploadedResult && (
          <div className="lg:col-span-7 sat-panel p-6 space-y-5 animate-fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A]/60">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="font-mono text-sm font-semibold text-slate-200 uppercase">
                  Dataset Successfully Ingested & Activated
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                ACTIVE WORKING DATASET
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Total Points</span>
                <span className="text-lg font-mono font-bold text-slate-100">{uploadedResult.total_rows}</span>
              </div>
              <div className="p-3 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Channels Extracted</span>
                <span className="text-lg font-mono font-bold text-cyan-300">{uploadedResult.channels?.length || 0}</span>
              </div>
              <div className="p-3 rounded bg-[#090F1C] border border-[#182642]">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Detected Anomalies</span>
                <span className="text-lg font-mono font-bold text-rose-400">{uploadedResult.total_anomalies || 0}</span>
              </div>
            </div>

            {/* Channels List Table */}
            <div>
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block mb-2 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                Channel Statistical Metrics
              </span>

              <div className="max-h-[280px] overflow-y-auto space-y-2 pr-1">
                {uploadedResult.channel_details?.map((ch: any) => (
                  <div key={ch.id} className="p-3 rounded bg-[#080E1C] border border-[#1E2D4A] flex items-center justify-between text-xs font-mono">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-100">{ch.id}</span>
                        <StatusBadge status={ch.status} size="sm" />
                      </div>
                      <span className="text-[10px] text-slate-400">{ch.subsystem}</span>
                    </div>

                    <div className="text-right">
                      <div className="text-slate-200">
                        Mean: <span className="text-cyan-300 font-bold">{ch.mean} {ch.unit}</span> (±{ch.std_dev})
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Min: {ch.min} | Max: {ch.max}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Navigation Actions */}
            <div className="pt-3 border-t border-[#1E2D4A]/60 flex flex-wrap items-center gap-3">
              <button
                onClick={() => navigate('/telemetry')}
                className="flex-1 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold uppercase flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_12px_rgba(0,229,255,0.3)] transition-all"
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Explore Telemetry</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => navigate('/anomalies')}
                className="py-2 px-3 rounded bg-[#101D36] hover:bg-[#182C4C] text-cyan-300 font-mono text-xs font-bold border border-cyan-500/40 flex items-center gap-1.5 cursor-pointer transition-colors"
              >
                <span>Anomalies</span>
              </button>

              <button
                onClick={() => navigate('/dashboard')}
                className="py-2 px-3 rounded bg-[#101D36] hover:bg-[#182C4C] text-slate-300 font-mono text-xs font-bold border border-[#1E2D4A] flex items-center gap-1.5 cursor-pointer transition-colors"
              >
                <Database className="w-3.5 h-3.5" />
                <span>Dashboard</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

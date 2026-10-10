import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { Upload, FileText, AlertTriangle, Loader2 } from 'lucide-react';
import { apiService } from '../services/api';

export const CustomUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const dataset = await apiService.upload(file);
      await apiService.setDataset(dataset.id); // ensure it's selected globally
      await apiService.runAnalysis("CustomChannel");
      navigate('/anomalies');
    } catch (err: any) {
      setError(err.message);
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

      <div className="sat-panel p-6 max-w-2xl mx-auto">
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
                <span className="text-emerald-400 font-bold">{file.name}</span>
              ) : (
                <span>Click to select or drag and drop a CSV file</span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-mono">Format: Timestamp, Feature1, Feature2...</p>
          </label>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className={`px-4 py-2 font-mono text-xs font-bold rounded flex items-center gap-2 transition-all ${
              !file || uploading
                ? 'bg-[#101D36] text-slate-500 cursor-not-allowed'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-[0_0_12px_rgba(0,229,255,0.4)]'
            }`}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Processing Data...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" /> Execute AI Pipeline
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
    </div>
  );
};

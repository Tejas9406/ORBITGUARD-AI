import { apiService } from './api';

export interface VisionDetection {
  id: string;
  label: string;
  category: 'STRUCTURAL' | 'THERMAL' | 'OPTICAL' | 'PAYLOAD';
  confidence: number;
  severity: 'CRITICAL' | 'WARNING' | 'NOMINAL';
  boundingBox: {
    x: number; // Normalized 0-100%
    y: number; // Normalized 0-100%
    width: number;
    height: number;
  };
  details: string;
  recommendation: string;
}

export interface VisionAnalysisResult {
  isSimulated: boolean;
  engineVersion: string;
  processedAt: string;
  domain?: string;
  imageMetrics?: {
    width: number;
    height: number;
    meanBrightness: number;
    contrast?: number;
    darkBackgroundRatio?: number;
    edgeDensity?: number;
  };
  totalDetections: number;
  criticalCount: number;
  detections: VisionDetection[];
  summary?: string;
}

export const runDemoVisionAnalysis = async (file: File): Promise<VisionAnalysisResult> => {
  return await apiService.analyzeVision(file);
};


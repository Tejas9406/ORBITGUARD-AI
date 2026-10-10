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
  totalDetections: number;
  criticalCount: number;
  detections: VisionDetection[];
}

export const runDemoVisionAnalysis = async (_file: File): Promise<VisionAnalysisResult> => {
  // Simulate honest model processing latency
  await new Promise((resolve) => setTimeout(resolve, 1400));

  // Deterministic realistic demo detections
  const detections: VisionDetection[] = [
    {
      id: 'DET-01',
      label: 'Solar Cell Micro-Fracture',
      category: 'STRUCTURAL',
      confidence: 96.4,
      severity: 'WARNING',
      boundingBox: {
        x: 28,
        y: 35,
        width: 18,
        height: 22,
      },
      details: 'Localized micro-cracking across photovoltaic junction array panel #3 caused by micrometeoroid impact.',
      recommendation: 'Cross-reference EPS channel P-1 voltage degradation during illuminated orbit phase.',
    },
    {
      id: 'DET-02',
      label: 'Thermal Blanket (MLI) Delamination',
      category: 'THERMAL',
      confidence: 91.8,
      severity: 'CRITICAL',
      boundingBox: {
        x: 62,
        y: 48,
        width: 24,
        height: 26,
      },
      details: 'Outer Kapton film tear exposing primary honeycomb bus frame to direct solar radiation.',
      recommendation: 'Immediate correlation with TCS sensor T-1 temperature spikes. Verify thermal bounds.',
    },
    {
      id: 'DET-03',
      label: 'Radiator Coating Discoloration',
      category: 'OPTICAL',
      confidence: 88.5,
      severity: 'WARNING',
      boundingBox: {
        x: 45,
        y: 72,
        width: 16,
        height: 18,
      },
      details: 'Atomic oxygen erosion observed on silverized Teflon thermal radiator surface.',
      recommendation: 'Monitor emissivity decay rate over subsequent passes.',
    },
  ];

  return {
    isSimulated: true,
    engineVersion: 'SatShield-Vision-Offline-Demo v1.0',
    processedAt: new Date().toISOString(),
    totalDetections: detections.length,
    criticalCount: detections.filter((d) => d.severity === 'CRITICAL').length,
    detections,
  };
};

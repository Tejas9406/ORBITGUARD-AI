import { useEffect, useRef, useState } from 'react';
import { Globe, Play, Pause } from 'lucide-react';

interface OrbitVisualizationProps {
  height?: number;
}

export const OrbitVisualization: React.FC<OrbitVisualizationProps> = ({ height = 260 }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isRotating, setIsRotating] = useState(true);
  const angleRef = useRef(0);
  const satAngleRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(centerX, centerY) * 0.65;

      ctx.clearRect(0, 0, width, height);

      // Deep space background gradient
      const bgGrad = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, radius * 1.5);
      bgGrad.addColorStop(0, '#0C162D');
      bgGrad.addColorStop(1, '#070B14');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Distant stars
      ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
      const stars = [
        [width * 0.15, height * 0.2],
        [width * 0.85, height * 0.15],
        [width * 0.1, height * 0.8],
        [width * 0.9, height * 0.75],
        [width * 0.7, height * 0.85],
        [width * 0.25, height * 0.4],
      ];
      stars.forEach(([sx, sy]) => {
        ctx.beginPath();
        ctx.arc(sx, sy, 1, 0, Math.PI * 2);
        ctx.fill();
      });

      // Earth atmospheric glow
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius * 1.05, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 229, 255, 0.08)';
      ctx.fill();

      // Earth Sphere body
      const earthGrad = ctx.createRadialGradient(
        centerX - radius * 0.3,
        centerY - radius * 0.3,
        radius * 0.1,
        centerX,
        centerY,
        radius
      );
      earthGrad.addColorStop(0, '#1E3A5F');
      earthGrad.addColorStop(0.7, '#0F2038');
      earthGrad.addColorStop(1, '#071224');
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = earthGrad;
      ctx.fill();
      ctx.strokeStyle = '#2A4A7A';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Latitude parallels
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
      ctx.lineWidth = 1;
      for (let lat = -60; lat <= 60; lat += 30) {
        const rad = (lat * Math.PI) / 180;
        const y = centerY + Math.sin(rad) * radius * 0.9;
        const rParallel = Math.cos(rad) * radius;
        ctx.beginPath();
        ctx.ellipse(centerX, y, rParallel, rParallel * 0.35, 0, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Meridians rotating
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)';
      for (let m = 0; m < 6; m++) {
        const mAngle = angleRef.current + (m * Math.PI) / 3;
        const xOffset = Math.sin(mAngle) * radius;
        ctx.beginPath();
        ctx.ellipse(centerX + xOffset * 0.5, centerY, Math.abs(xOffset) * 0.5, radius, 0, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Orbit plane ellipse (inclined polar LEO orbit)
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.45)';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, radius * 1.45, radius * 0.65, -0.4, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Satellite position calculation along ellipse
      const satOrbitRadiusX = radius * 1.45;
      const satOrbitRadiusY = radius * 0.65;
      const tilt = -0.4;
      const cosT = Math.cos(tilt);
      const sinT = Math.sin(tilt);

      const rawX = Math.cos(satAngleRef.current) * satOrbitRadiusX;
      const rawY = Math.sin(satAngleRef.current) * satOrbitRadiusY;

      const satX = centerX + (rawX * cosT - rawY * sinT);
      const satY = centerY + (rawX * sinT + rawY * cosT);

      // Satellite footprint
      ctx.beginPath();
      ctx.arc(satX, satY, 14, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 229, 255, 0.15)';
      ctx.fill();

      // Satellite beacon
      ctx.beginPath();
      ctx.arc(satX, satY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#00E5FF';
      ctx.shadowColor = '#00E5FF';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Label satellite
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.fillStyle = '#E2E8F0';
      ctx.fillText('SATSHIELD-1', satX + 8, satY - 6);

      if (isRotating) {
        angleRef.current += 0.004;
        satAngleRef.current += 0.012;
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isRotating]);

  return (
    <div className="sat-panel p-3 flex flex-col relative overflow-hidden">
      <div className="flex items-center justify-between pb-2 mb-1 border-b border-[#1E2D4A]/60">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-cyan-400" />
          <span className="font-mono text-xs font-semibold text-slate-200">
            ORBIT PASS GEOMETRY
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-950/60 text-amber-400 border border-amber-500/30">
            Illustrative Visualization
          </span>
        </div>

        <button
          onClick={() => setIsRotating((prev) => !prev)}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300 transition-colors"
          title={isRotating ? 'Pause orbital motion' : 'Resume orbital motion'}
          aria-label={isRotating ? 'Pause orbital motion' : 'Resume orbital motion'}
        >
          {isRotating ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        </button>
      </div>

      <div className="relative flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={480}
          height={height}
          className="w-full h-auto max-h-[260px] rounded"
        />

        <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[10px] font-mono text-slate-400 bg-[#070B14]/80 px-2.5 py-1 rounded border border-[#1E2D4A]/50 backdrop-blur-xs">
          <span>ORBIT: Sun-Synch LEO 550km</span>
          <span className="text-cyan-400">INCLINATION: 97.4°</span>
          <span>PERIOD: ~95m</span>
        </div>
      </div>
    </div>
  );
};

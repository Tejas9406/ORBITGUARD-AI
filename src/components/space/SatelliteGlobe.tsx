import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GlassPanel } from '../common/GlassPanel';
import { SatelliteInfoPanel } from './SatelliteInfoPanel';
import type { SatelliteStatus, GroundStation } from '../../types/satellite';
import {
  Globe,
  RotateCcw,
  Play,
  Pause,
  ZoomIn,
  ZoomOut,
  Info,
} from 'lucide-react';

interface SatelliteGlobeProps {
  status?: SatelliteStatus;
  healthScore?: number;
  activeAnomaliesCount?: number;
  height?: number;
  className?: string;
  onNavigateTelemetry?: () => void;
  onNavigateAnomaly?: () => void;
}

const GROUND_STATIONS: GroundStation[] = [
  { id: 'SHADNAGAR', name: 'ISRO NRSC Shadnagar', latitude: 17.03, longitude: 78.21, elevationM: 650 },
  { id: 'ISTRAC', name: 'ISRO ISTRAC Bengaluru', latitude: 12.97, longitude: 77.59, elevationM: 920 },
  { id: 'SVALBARD', name: 'Svalbard Polar Pass', latitude: 78.22, longitude: 15.65, elevationM: 400 },
];

export const SatelliteGlobe: React.FC<SatelliteGlobeProps> = ({
  status = 'CRITICAL',
  healthScore = 84,
  activeAnomaliesCount = 2,
  height = 420,
  className = '',
  onNavigateTelemetry,
  onNavigateAnomaly,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [isRotating, setIsRotating] = useState<boolean>(true);
  const [isInfoOpen, setIsInfoOpen] = useState<boolean>(false);
  const [currentSubpoint, setCurrentSubpoint] = useState<{ lat: number; lon: number; alt: number }>({
    lat: 18.42,
    lon: 78.53,
    alt: 552.4,
  });

  // Three.js instances ref
  const threeRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    earthGroup: THREE.Group;
    satelliteMesh: THREE.Mesh;
    orbitLine: THREE.Line;
    footprintMesh: THREE.Mesh;
    orbitPoints: THREE.Vector3[];
    animId: number;
  } | null>(null);

  // Convert Lat/Lon/Alt to 3D Sphere Vector
  const latLonToVector3 = useCallback((lat: number, lon: number, radius: number): THREE.Vector3 => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
  }, []);

  // Generate lightweight procedural Earth Texture (continents + technical graticules)
  const createProceduralEarthTexture = (): THREE.CanvasTexture => {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext('2d')!;

    // Deep space ocean background
    ctx.fillStyle = '#081224';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Subtle continent geometries
    ctx.fillStyle = '#102242';
    // North America
    ctx.beginPath();
    ctx.ellipse(250, 160, 110, 80, -0.2, 0, Math.PI * 2);
    ctx.fill();
    // South America
    ctx.beginPath();
    ctx.ellipse(320, 340, 60, 95, 0.2, 0, Math.PI * 2);
    ctx.fill();
    // Eurasia
    ctx.beginPath();
    ctx.ellipse(680, 160, 180, 85, 0.1, 0, Math.PI * 2);
    ctx.fill();
    // Africa
    ctx.beginPath();
    ctx.ellipse(540, 270, 75, 110, 0, 0, Math.PI * 2);
    ctx.fill();
    // Australia
    ctx.beginPath();
    ctx.ellipse(820, 360, 60, 45, 0, 0, Math.PI * 2);
    ctx.fill();
    // Indian Subcontinent Highlight
    ctx.fillStyle = '#16325C';
    ctx.beginPath();
    ctx.moveTo(710, 210);
    ctx.lineTo(745, 275);
    ctx.lineTo(765, 220);
    ctx.closePath();
    ctx.fill();

    // Technical Graticules (Latitude & Longitude parallels)
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= canvas.width; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += 42) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Equator highlight
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.45)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();

    const texture = new THREE.CanvasTexture(canvas);
    return texture;
  };

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 600;
    const currentHeight = height;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050811);

    const camera = new THREE.PerspectiveCamera(40, width / currentHeight, 0.1, 1000);
    camera.position.set(0, 5, 14);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, currentHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Ambient & Directional Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0x00E5FF, 1.2);
    sunLight.position.set(12, 10, 15);
    scene.add(sunLight);

    // Deep space starfield
    const starGeo = new THREE.BufferGeometry();
    const starCount = 300;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPos[i] = (Math.random() - 0.5) * 80;
      starPos[i + 1] = (Math.random() - 0.5) * 80;
      starPos[i + 2] = (Math.random() - 0.5) * 80;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: 0x64748B, size: 0.12, transparent: true, opacity: 0.6 });
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // Earth Group
    const earthGroup = new THREE.Group();
    scene.add(earthGroup);

    // Earth Sphere
    const earthRadius = 3.6;
    const earthGeo = new THREE.SphereGeometry(earthRadius, 48, 48);
    const earthTexture = createProceduralEarthTexture();
    const earthMat = new THREE.MeshPhongMaterial({
      map: earthTexture,
      bumpScale: 0.05,
      specular: new THREE.Color(0x0A2045),
      shininess: 15,
    });
    const earthMesh = new THREE.Mesh(earthGeo, earthMat);
    earthGroup.add(earthMesh);

    // Atmospheric Glow Outer Sphere
    const atmosGeo = new THREE.SphereGeometry(earthRadius * 1.04, 32, 32);
    const atmosMat = new THREE.MeshBasicMaterial({
      color: 0x00E5FF,
      transparent: true,
      opacity: 0.08,
      side: THREE.BackSide,
    });
    const atmosMesh = new THREE.Mesh(atmosGeo, atmosMat);
    earthGroup.add(atmosMesh);

    // Orbital Path Calculation (Sun-Synchronous Polar LEO ~550km, inclined 97.4°)
    const orbitRadius = earthRadius + 0.85; // ~550km proportional altitude
    const orbitPoints: THREE.Vector3[] = [];
    const inclination = (97.4 * Math.PI) / 180;
    const segments = 128;

    for (let i = 0; i <= segments; i++) {
      const u = (i / segments) * Math.PI * 2;
      const x = orbitRadius * Math.cos(u);
      const y = orbitRadius * Math.sin(u) * Math.sin(inclination);
      const z = orbitRadius * Math.sin(u) * Math.cos(inclination);
      orbitPoints.push(new THREE.Vector3(x, y, z));
    }

    const orbitGeo = new THREE.BufferGeometry().setFromPoints(orbitPoints);
    const orbitColor = status === 'CRITICAL' ? 0xEF4444 : status === 'WARNING' ? 0xF59E0B : 0x00E5FF;
    const orbitMat = new THREE.LineBasicMaterial({
      color: orbitColor,
      transparent: true,
      opacity: 0.65,
    });
    const orbitLine = new THREE.Line(orbitGeo, orbitMat);
    scene.add(orbitLine);

    // Ground Track Footprint (sub-satellite projection)
    const footprintGeo = new THREE.RingGeometry(0.35, 0.45, 32);
    const footprintMat = new THREE.MeshBasicMaterial({
      color: 0x00E5FF,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide,
    });
    const footprintMesh = new THREE.Mesh(footprintGeo, footprintMat);
    footprintMesh.rotation.x = Math.PI / 2;
    earthGroup.add(footprintMesh);

    // Satellite Mesh Model
    const satGroup = new THREE.Group();
    // Central body
    const satBodyGeo = new THREE.BoxGeometry(0.24, 0.24, 0.32);
    const satBodyMat = new THREE.MeshStandardMaterial({
      color: 0xD9E2EC,
      metalness: 0.8,
      roughness: 0.2,
    });
    const satBody = new THREE.Mesh(satBodyGeo, satBodyMat);
    satGroup.add(satBody);

    // Solar array wings
    const solarGeo = new THREE.BoxGeometry(0.8, 0.18, 0.02);
    const solarMat = new THREE.MeshStandardMaterial({
      color: 0x0369A1,
      metalness: 0.9,
      roughness: 0.1,
    });
    const solarWing = new THREE.Mesh(solarGeo, solarMat);
    satGroup.add(solarWing);

    // Status beacon light on satellite
    const beaconColor = status === 'CRITICAL' ? 0xEF4444 : status === 'WARNING' ? 0xF59E0B : 0x00E5FF;
    const beaconLight = new THREE.PointLight(beaconColor, 2, 2.5);
    satGroup.add(beaconLight);

    // Beacon marker sphere
    const beaconSphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const beaconSphereMat = new THREE.MeshBasicMaterial({ color: beaconColor });
    const beaconSphere = new THREE.Mesh(beaconSphereGeo, beaconSphereMat);
    satGroup.add(beaconSphere);

    scene.add(satGroup);

    // Ground Station Markers
    const stationsGroup = new THREE.Group();
    GROUND_STATIONS.forEach((gs) => {
      const pos = latLonToVector3(gs.latitude, gs.longitude, earthRadius + 0.02);
      const markerGeo = new THREE.SphereGeometry(0.08, 12, 12);
      const markerMat = new THREE.MeshBasicMaterial({ color: 0x38BDF8 });
      const marker = new THREE.Mesh(markerGeo, markerMat);
      marker.position.copy(pos);
      stationsGroup.add(marker);
    });
    earthGroup.add(stationsGroup);

    // Initial positioning
    camera.lookAt(0, 0, 0);

    // Mouse drag interaction to rotate globe
    let isDragging = false;
    let prevMousePos = { x: 0, y: 0 };

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMousePos = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMousePos.x;
      const deltaY = e.clientY - prevMousePos.y;
      earthGroup.rotation.y += deltaX * 0.005;
      earthGroup.rotation.x += deltaY * 0.005;
      prevMousePos = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const domNode = renderer.domElement;
    domNode.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Satellite Animation Loop
    let orbitAngle = 0;
    const renderLoop = () => {
      // Rotate Earth slowly
      if (isRotating) {
        earthGroup.rotation.y += 0.0015;
      }

      // Propagate satellite along orbit ring
      orbitAngle += 0.006;
      const u = orbitAngle;
      const satX = orbitRadius * Math.cos(u);
      const satY = orbitRadius * Math.sin(u) * Math.sin(inclination);
      const satZ = orbitRadius * Math.sin(u) * Math.cos(inclination);
      satGroup.position.set(satX, satY, satZ);
      satGroup.lookAt(0, 0, 0);

      // Project sub-satellite footprint on Earth surface
      const subpointNorm = new THREE.Vector3(satX, satY, satZ).normalize();
      const subPos = subpointNorm.clone().multiplyScalar(earthRadius + 0.02);
      footprintMesh.position.copy(subPos);
      footprintMesh.lookAt(subpointNorm.clone().multiplyScalar(10));

      // Calculate approximate subsatellite lat/lon
      const currentLat = (Math.asin(subpointNorm.y) * 180) / Math.PI;
      const currentLon = ((Math.atan2(subpointNorm.z, -subpointNorm.x) * 180) / Math.PI) - (earthGroup.rotation.y * 180) / Math.PI;
      const normalizedLon = ((currentLon + 180) % 360) - 180;

      // Update state sparingly to avoid React thrash
      if (Math.round(orbitAngle * 10) % 5 === 0) {
        setCurrentSubpoint({
          lat: parseFloat(currentLat.toFixed(2)),
          lon: parseFloat(normalizedLon.toFixed(2)),
          alt: 552.4,
        });
      }

      renderer.render(scene, camera);
      const animId = requestAnimationFrame(renderLoop);
      if (threeRef.current) threeRef.current.animId = animId;
    };

    const animId = requestAnimationFrame(renderLoop);

    threeRef.current = {
      renderer,
      scene,
      camera,
      earthGroup,
      satelliteMesh: satBody,
      orbitLine,
      footprintMesh,
      orbitPoints,
      animId,
    };

    // Responsive resize handler
    const handleResize = () => {
      if (!container || !threeRef.current) return;
      const w = container.clientWidth;
      threeRef.current.camera.aspect = w / currentHeight;
      threeRef.current.camera.updateProjectionMatrix();
      threeRef.current.renderer.setSize(w, currentHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      domNode.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      renderer.dispose();
      earthGeo.dispose();
      earthMat.dispose();
      earthTexture.dispose();
    };
  }, [height, status, isRotating, latLonToVector3]);

  const handleResetView = () => {
    if (threeRef.current) {
      threeRef.current.earthGroup.rotation.set(0, 0, 0);
      threeRef.current.camera.position.set(0, 5, 14);
      threeRef.current.camera.lookAt(0, 0, 0);
    }
  };

  const handleZoom = (delta: number) => {
    if (threeRef.current) {
      const cam = threeRef.current.camera;
      const newZ = Math.max(8, Math.min(22, cam.position.z + delta));
      cam.position.z = newZ;
    }
  };

  return (
    <GlassPanel cornerAccents={true} padding="none" className={`relative flex flex-col overflow-hidden ${className}`}>
      {/* Top Header & Space Geometry Status */}
      <div className="p-3.5 border-b border-[#1A2E50]/70 flex items-center justify-between z-10 bg-[#070D1B]/80 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-cyan-400" />
          <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-100 flex items-center gap-2">
            3D Satellite Orbit Geometry
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/70 text-cyan-300 border border-cyan-500/40">
            SATSHIELD-OBS-1
          </span>
          <span className="hidden sm:inline text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-500/30">
            ILLUSTRATIVE ORBITAL VISUALIZATION
          </span>
        </div>

        {/* Toolbar action buttons */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setIsRotating((prev) => !prev)}
            className="p-1.5 rounded bg-[#101D36] hover:bg-[#182C4C] text-slate-300 border border-[#1E355B] text-xs transition-colors"
            title={isRotating ? 'Pause orbital rotation' : 'Resume rotation'}
          >
            {isRotating ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={() => handleZoom(-1.5)}
            className="p-1.5 rounded bg-[#101D36] hover:bg-[#182C4C] text-slate-300 border border-[#1E355B] text-xs transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => handleZoom(1.5)}
            className="p-1.5 rounded bg-[#101D36] hover:bg-[#182C4C] text-slate-300 border border-[#1E355B] text-xs transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleResetView}
            className="p-1.5 rounded bg-[#101D36] hover:bg-[#182C4C] text-slate-300 border border-[#1E355B] text-xs transition-colors"
            title="Reset view camera"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setIsInfoOpen((prev) => !prev)}
            className={`p-1.5 rounded border text-xs transition-colors ${
              isInfoOpen
                ? 'bg-cyan-950 text-cyan-300 border-cyan-400'
                : 'bg-[#101D36] text-slate-300 border-[#1E355B]'
            }`}
            title="Toggle satellite telemetry panel"
          >
            <Info className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 3D WebGL Canvas Container */}
      <div className="relative w-full" style={{ height }}>
        <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Live Subsatellite Coordinates Overlay */}
        <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 text-[11px] font-mono text-slate-300 bg-[#070D1B]/85 px-3 py-1.5 rounded border border-[#16294A] backdrop-blur-md">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            SUBPOINT: <b className="text-cyan-300">{currentSubpoint.lat}° N, {currentSubpoint.lon}° E</b>
          </span>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <span className="hidden sm:inline text-slate-400">ALT: {currentSubpoint.alt} km</span>
          <span className="text-slate-600 hidden sm:inline">•</span>
          <span className="hidden sm:inline text-amber-400">STATUS: {status}</span>
        </div>

        {/* Clickable Satellite Marker Trigger */}
        <div className="absolute top-4 left-4 z-10">
          <button
            onClick={() => setIsInfoOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#081226]/90 border border-cyan-500/50 hover:border-cyan-400 text-xs font-mono text-slate-200 backdrop-blur-md shadow-lg transition-all"
          >
            <span className={`w-2.5 h-2.5 rounded-full ${
              status === 'CRITICAL' ? 'bg-rose-500 animate-ping' : status === 'WARNING' ? 'bg-amber-400' : 'bg-cyan-400'
            }`} />
            <span>SATSHIELD-OBS-1</span>
            <span className="text-[10px] text-cyan-400 font-bold">INSPECT →</span>
          </button>
        </div>

        {/* Glass Satellite Information Panel (Overlay) */}
        {isInfoOpen && (
          <div className="absolute top-4 right-4 z-20 w-84 max-w-[90%] animate-in fade-in zoom-in-95 duration-150">
            <SatelliteInfoPanel
              satelliteId="SATSHIELD-OBS-1"
              orbitType="Sun-Synchronous Polar LEO (~550 km)"
              altitudeKm={currentSubpoint.alt}
              latitude={currentSubpoint.lat}
              longitude={currentSubpoint.lon}
              status={status}
              healthScore={healthScore}
              activeAnomaliesCount={activeAnomaliesCount}
              onViewTelemetry={onNavigateTelemetry}
              onInvestigateAnomaly={onNavigateAnomaly}
              onClose={() => setIsInfoOpen(false)}
            />
          </div>
        )}
      </div>
    </GlassPanel>
  );
};

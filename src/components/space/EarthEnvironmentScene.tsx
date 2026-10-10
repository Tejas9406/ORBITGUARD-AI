import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { earthModelLoader } from '../../services/earthModelLoader';
import { SATELLITE_DIRECTORY } from '../../data/satelliteDirectory';
import type { SatelliteMetadata, GroundStation } from '../../types/satellite';
import {
  Globe,
  RotateCcw,
  Play,
  Pause,
  ZoomIn,
  ZoomOut,
  Info,
  Layers,
  Cpu,
  Compass,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface EarthEnvironmentSceneProps {
  mode?: 'cinematic' | 'dashboard';
  height?: number;
  className?: string;
  selectedSatelliteId?: string;
  onSelectSatellite?: (sat: SatelliteMetadata) => void;
  showUIOverlay?: boolean;
}

const GROUND_STATIONS: GroundStation[] = [
  { id: 'SHADNAGAR', name: 'ISRO NRSC Shadnagar', latitude: 17.03, longitude: 78.21, elevationM: 650 },
  { id: 'ISTRAC', name: 'ISRO ISTRAC Bengaluru', latitude: 12.97, longitude: 77.59, elevationM: 920 },
  { id: 'SVALBARD', name: 'Svalbard Polar Pass', latitude: 78.22, longitude: 15.65, elevationM: 400 },
];

export const EarthEnvironmentScene: React.FC<EarthEnvironmentSceneProps> = ({
  mode = 'dashboard',
  height = 480,
  className = '',
  selectedSatelliteId,
  onSelectSatellite,
  showUIOverlay = true,
}) => {
  const navigate = useNavigate();
  const mountRef = useRef<HTMLDivElement | null>(null);

  // Loading & State
  const [loadPercent, setLoadPercent] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUsingFallback, setIsUsingFallback] = useState<boolean>(false);
  const [isRotating, setIsRotating] = useState<boolean>(true);
  const [isInfoOpen, setIsInfoOpen] = useState<boolean>(false);
  const [isLayersOpen, setIsLayersOpen] = useState<boolean>(false);

  // Active Selected Satellite
  const [selectedSat, setSelectedSat] = useState<SatelliteMetadata>(() => {
    if (selectedSatelliteId) {
      const match = SATELLITE_DIRECTORY.find((s) => s.id === selectedSatelliteId);
      if (match) return match;
    }
    return SATELLITE_DIRECTORY[0];
  });

  const selectedSatRef = useRef<SatelliteMetadata>(selectedSat);
  useEffect(() => {
    selectedSatRef.current = selectedSat;
  }, [selectedSat]);

  // Sync external selection prop
  useEffect(() => {
    if (selectedSatelliteId) {
      const match = SATELLITE_DIRECTORY.find((s) => s.id === selectedSatelliteId);
      if (match && match.id !== selectedSat.id) {
        setSelectedSat(match);
      }
    }
  }, [selectedSatelliteId, selectedSat.id]);

  // Layer Toggles
  const [layers, setLayers] = useState({
    orbitPaths: true,
    satellites: true,
    groundStations: true,
    atmosphereGlow: true,
  });

  // Lat / Lon conversion to 3D sphere coordinate
  const latLonToVector3 = useCallback((lat: number, lon: number, radius: number): THREE.Vector3 => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
  }, []);

  // Three.js instances ref
  const threeRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    earthGroup: THREE.Group;
    orbitGroup: THREE.Group;
    groundStationGroup: THREE.Group;
    atmosphereMesh: THREE.Mesh;
    satVisuals: {
      id: string;
      mesh: THREE.Group;
      orbitRadius: number;
      inc: number;
      speed: number;
      angle: number;
      orbitLine: THREE.Line;
      reticle: THREE.Mesh;
    }[];
    animId: number;
    disposables: { dispose: () => void }[];
  } | null>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    let isSubscribed = true;
    const width = container.clientWidth || (mode === 'cinematic' ? window.innerWidth : 800);
    const currentHeight = height;

    const disposables: { dispose: () => void }[] = [];

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x02050e);

    const fov = mode === 'cinematic' ? 42 : 38;
    const camera = new THREE.PerspectiveCamera(fov, width / currentHeight, 0.1, 1000);
    const initCamPos = mode === 'cinematic' ? new THREE.Vector3(0, 0.2, 11.8) : new THREE.Vector3(0, 1.2, 12.8);
    camera.position.copy(initCamPos);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, currentHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = mode === 'cinematic' ? 1.55 : 1.4;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Cinematic Brilliant Planetary Lighting: Sunlight Key, Fill, Front Key, and Radiant Bluish Rim Fade
    const targetX = mode === 'cinematic' ? 2.9 : 0;
    const targetY = mode === 'cinematic' ? 0.25 : 0.8;

    const ambientLight = new THREE.AmbientLight(0xffffff, mode === 'cinematic' ? 1.4 : 0.75);
    scene.add(ambientLight);

    // Directional Sunlight (Bright radiant sunbeam across continents and oceans)
    const sunLight = new THREE.DirectionalLight(0xfffaea, mode === 'cinematic' ? 2.8 : 2.5);
    sunLight.position.set(targetX + 8, targetY + 6, 12);
    sunLight.target.position.set(targetX, targetY, 0);
    scene.add(sunLight.target);
    scene.add(sunLight);

    // Cool Sky Fill & Backlight (Starlight back-scatter)
    const fillLight = new THREE.DirectionalLight(0x00b4ff, mode === 'cinematic' ? 1.3 : 0.65);
    fillLight.position.set(targetX - 12, targetY - 4, -4);
    fillLight.target.position.set(targetX, targetY, 0);
    scene.add(fillLight.target);
    scene.add(fillLight);

    // Direct Front Illuminator (Directly brightens camera-facing continents, eliminating dark dull shadows)
    const frontKeyLight = new THREE.DirectionalLight(0xe8f2ff, mode === 'cinematic' ? 2.0 : 1.0);
    frontKeyLight.position.set(targetX, targetY + 1, 14);
    frontKeyLight.target.position.set(targetX, targetY, 0);
    scene.add(frontKeyLight.target);
    scene.add(frontKeyLight);

    // Radiant Bluish Rim Fade Lighting
    const blueRimLight = new THREE.DirectionalLight(0x00d4ff, mode === 'cinematic' ? 2.4 : 1.6);
    blueRimLight.position.set(targetX - 14, targetY + 6, -8);
    blueRimLight.target.position.set(targetX, targetY, 0);
    scene.add(blueRimLight.target);
    scene.add(blueRimLight);

    // Subtle celestial point radiance for high orbital satellites
    const celestialRadiance = new THREE.PointLight(0x60a5fa, mode === 'cinematic' ? 1.1 : 0.7, 60);
    celestialRadiance.position.set(targetX, targetY + 12, 12);
    scene.add(celestialRadiance);

    // 3. Cinematic Multi-Layer Twinkling & Glowing Celestial Starfield
    const starUniforms = {
      uTime: { value: 0 },
    };

    // Layer A: Twinkling Deep Space Starfield (2600 Stars)
    const starCountA = 2600;
    const starGeoA = new THREE.BufferGeometry();
    const starPosA = new Float32Array(starCountA * 3);
    const starColorA = new Float32Array(starCountA * 3);
    const starSizeA = new Float32Array(starCountA);
    const starPhaseA = new Float32Array(starCountA);
    const starSpeedA = new Float32Array(starCountA);

    for (let i = 0; i < starCountA; i++) {
      const r = 50 + Math.random() * 110;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      starPosA[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPosA[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      starPosA[i * 3 + 2] = r * Math.cos(phi);

      const type = Math.random();
      if (type > 0.8) {
        // Class O/B: Sapphire blue-white
        starColorA[i * 3] = 0.65;
        starColorA[i * 3 + 1] = 0.85;
        starColorA[i * 3 + 2] = 1.0;
        starSizeA[i] = 2.4 + Math.random() * 2.0;
      } else if (type > 0.55) {
        // Class A/F: Pure diamond white
        starColorA[i * 3] = 0.96;
        starColorA[i * 3 + 1] = 0.98;
        starColorA[i * 3 + 2] = 1.0;
        starSizeA[i] = 1.8 + Math.random() * 1.8;
      } else if (type > 0.3) {
        // Class G/K: Solar gold / amber
        starColorA[i * 3] = 1.0;
        starColorA[i * 3 + 1] = 0.88;
        starColorA[i * 3 + 2] = 0.62;
        starSizeA[i] = 2.0 + Math.random() * 1.6;
      } else if (type > 0.15) {
        // Class M: Warm flame orange
        starColorA[i * 3] = 1.0;
        starColorA[i * 3 + 1] = 0.68;
        starColorA[i * 3 + 2] = 0.48;
        starSizeA[i] = 1.9 + Math.random() * 1.5;
      } else {
        // ISRO telemetry cyan highlight
        starColorA[i * 3] = 0.25;
        starColorA[i * 3 + 1] = 0.95;
        starColorA[i * 3 + 2] = 1.0;
        starSizeA[i] = 2.5 + Math.random() * 1.8;
      }

      starPhaseA[i] = Math.random() * Math.PI * 2;
      starSpeedA[i] = 1.5 + Math.random() * 3.5;
    }

    starGeoA.setAttribute('position', new THREE.BufferAttribute(starPosA, 3));
    starGeoA.setAttribute('aColor', new THREE.BufferAttribute(starColorA, 3));
    starGeoA.setAttribute('aSize', new THREE.BufferAttribute(starSizeA, 1));
    starGeoA.setAttribute('aPhase', new THREE.BufferAttribute(starPhaseA, 1));
    starGeoA.setAttribute('aSpeed', new THREE.BufferAttribute(starSpeedA, 1));
    disposables.push(starGeoA);

    const starMatA = new THREE.ShaderMaterial({
      uniforms: starUniforms,
      vertexShader: `
        uniform float uTime;
        attribute float aSize;
        attribute vec3 aColor;
        attribute float aPhase;
        attribute float aSpeed;
        varying vec3 vColor;
        varying float vTwinkle;

        void main() {
          vColor = aColor;
          float tw = 0.5 + 0.35 * sin(uTime * aSpeed + aPhase) + 0.15 * sin(uTime * (aSpeed * 1.8) + aPhase * 2.3);
          vTwinkle = clamp(tw, 0.12, 1.0);

          vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = (aSize * (0.75 + 0.45 * vTwinkle)) * (340.0 / -mvPos.z);
          gl_Position = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vTwinkle;

        void main() {
          vec2 p = gl_PointCoord - vec2(0.5);
          float dist = length(p);
          if (dist > 0.5) discard;

          float core = exp(-dist * dist * 38.0);
          float halo = exp(-dist * 6.2) * 0.55;
          float spike = (exp(-abs(p.x) * 26.0) * exp(-abs(p.y) * 4.2) +
                         exp(-abs(p.y) * 26.0) * exp(-abs(p.x) * 4.2)) * 0.22;

          float intensity = (core + halo + spike * vTwinkle) * (0.35 + 0.65 * vTwinkle);
          vec3 finalColor = mix(vColor, vec3(1.0, 1.0, 1.0), core * 0.88);

          gl_FragColor = vec4(finalColor, intensity);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    disposables.push(starMatA);
    const starFieldA = new THREE.Points(starGeoA, starMatA);
    scene.add(starFieldA);

    // Layer B: Major Navigational Beacon Stars (Luminous glowing celestial points)
    const navStarCount = 56;
    const navStarGeo = new THREE.BufferGeometry();
    const navStarPos = new Float32Array(navStarCount * 3);
    const navStarColor = new Float32Array(navStarCount * 3);
    const navStarSize = new Float32Array(navStarCount);
    const navStarPhase = new Float32Array(navStarCount);
    const navStarSpeed = new Float32Array(navStarCount);

    for (let i = 0; i < navStarCount; i++) {
      const r = 70 + Math.random() * 80;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      navStarPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      navStarPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      navStarPos[i * 3 + 2] = r * Math.cos(phi);

      const navType = i % 4;
      if (navType === 0) {
        navStarColor[i * 3] = 0.7; // Sirius / Vega blue-white
        navStarColor[i * 3 + 1] = 0.9;
        navStarColor[i * 3 + 2] = 1.0;
      } else if (navType === 1) {
        navStarColor[i * 3] = 1.0; // Canopus diamond pure white
        navStarColor[i * 3 + 1] = 1.0;
        navStarColor[i * 3 + 2] = 1.0;
      } else if (navType === 2) {
        navStarColor[i * 3] = 1.0; // Arcturus golden
        navStarColor[i * 3 + 1] = 0.85;
        navStarColor[i * 3 + 2] = 0.55;
      } else {
        navStarColor[i * 3] = 0.0; // Cyan navigation beacon
        navStarColor[i * 3 + 1] = 0.95;
        navStarColor[i * 3 + 2] = 1.0;
      }

      navStarSize[i] = 5.5 + Math.random() * 3.5;
      navStarPhase[i] = Math.random() * Math.PI * 2;
      navStarSpeed[i] = 1.0 + Math.random() * 2.0;
    }

    navStarGeo.setAttribute('position', new THREE.BufferAttribute(navStarPos, 3));
    navStarGeo.setAttribute('aColor', new THREE.BufferAttribute(navStarColor, 3));
    navStarGeo.setAttribute('aSize', new THREE.BufferAttribute(navStarSize, 1));
    navStarGeo.setAttribute('aPhase', new THREE.BufferAttribute(navStarPhase, 1));
    navStarGeo.setAttribute('aSpeed', new THREE.BufferAttribute(navStarSpeed, 1));
    disposables.push(navStarGeo);

    const navStarMat = new THREE.ShaderMaterial({
      uniforms: starUniforms,
      vertexShader: `
        uniform float uTime;
        attribute float aSize;
        attribute vec3 aColor;
        attribute float aPhase;
        attribute float aSpeed;
        varying vec3 vColor;
        varying float vTwinkle;

        void main() {
          vColor = aColor;
          float tw = 0.55 + 0.45 * sin(uTime * aSpeed + aPhase);
          vTwinkle = tw;

          vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = (aSize * (0.8 + 0.4 * vTwinkle)) * (360.0 / -mvPos.z);
          gl_Position = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vTwinkle;

        void main() {
          vec2 p = gl_PointCoord - vec2(0.5);
          float dist = length(p);
          if (dist > 0.5) discard;

          // Glowing celestial beacon with diamond flare
          float core = exp(-dist * dist * 44.0);
          float halo = exp(-dist * 5.5) * 0.7;
          float spike = (exp(-abs(p.x) * 20.0) * exp(-abs(p.y) * 3.5) +
                         exp(-abs(p.y) * 20.0) * exp(-abs(p.x) * 3.5)) * 0.35;

          float intensity = (core + halo + spike * vTwinkle) * (0.45 + 0.55 * vTwinkle);
          vec3 finalColor = mix(vColor, vec3(1.0, 1.0, 1.0), core * 0.92);

          gl_FragColor = vec4(finalColor, intensity);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    disposables.push(navStarMat);
    const navStarField = new THREE.Points(navStarGeo, navStarMat);
    scene.add(navStarField);

    // Layer C: Subtle Cosmic Dust Particles
    const dustCount = 200;
    const dustGeo = new THREE.BufferGeometry();
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount * 3; i += 3) {
      dustPos[i] = (Math.random() - 0.5) * 90;
      dustPos[i + 1] = (Math.random() - 0.5) * 90;
      dustPos[i + 2] = (Math.random() - 0.5) * 90;
    }
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    disposables.push(dustGeo);
    const dustMat = new THREE.PointsMaterial({
      size: 0.35,
      color: 0x0088cc,
      transparent: true,
      opacity: 0.28,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    disposables.push(dustMat);
    const dustField = new THREE.Points(dustGeo, dustMat);
    scene.add(dustField);

    // 4. Earth Master Rotation Group (Locked order YXZ)
    // Elegantly sized Earth (2.75 for landing, 3.8 for dashboard) centered vertically and right-aligned
    const earthRadius = mode === 'cinematic' ? 2.75 : 3.8;
    const earthPosX = mode === 'cinematic' ? 2.9 : 0;
    const earthPosY = mode === 'cinematic' ? 0.25 : 0.8;

    const earthGroup = new THREE.Group();
    earthGroup.rotation.order = 'YXZ';
    earthGroup.position.set(earthPosX, earthPosY, 0);
    scene.add(earthGroup);

    // 5. Atmospheric Fresnel Rim Glow Shader with Smooth Bluish Fade (Requirement 3)
    const atmosRadius = earthRadius * 1.018;
    const atmosGeo = new THREE.SphereGeometry(atmosRadius, 64, 64);
    disposables.push(atmosGeo);
    const atmosMat = new THREE.ShaderMaterial({
      uniforms: {
        uSunDir: { value: sunLight.position.clone().normalize() },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        varying vec3 vWorldNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vWorldNormal = normalize((modelMatrix * vec4(normal, 0.0)).xyz);
          vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uSunDir;
        varying vec3 vNormal;
        varying vec3 vPosition;
        varying vec3 vWorldNormal;
        void main() {
          vec3 viewDir = normalize(-vPosition);
          // Smooth atmospheric grazing limb fade
          float fresnel = pow(1.0 - max(0.0, dot(vNormal, viewDir)), 2.4);
          float sunFactor = max(0.0, dot(vWorldNormal, normalize(uSunDir)) * 0.5 + 0.5);
          vec3 dayAtmosphere = vec3(0.05, 0.82, 1.0);
          vec3 nightAtmosphere = vec3(0.02, 0.35, 0.85);
          vec3 atmosColor = mix(nightAtmosphere, dayAtmosphere, sunFactor);
          gl_FragColor = vec4(atmosColor, 1.0) * (fresnel * (0.6 + 0.65 * sunFactor));
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.FrontSide,
      transparent: true,
      depthWrite: false,
    });
    disposables.push(atmosMat);
    const atmosphereMesh = new THREE.Mesh(atmosGeo, atmosMat);
    atmosphereMesh.visible = layers.atmosphereGlow;
    earthGroup.add(atmosphereMesh);

    // 6. Ground Tracking Station Markers (Resting on Earth continents)
    const groundStationGroup = new THREE.Group();
    earthGroup.add(groundStationGroup);

    GROUND_STATIONS.forEach((gs) => {
      const pos = latLonToVector3(gs.latitude, gs.longitude, earthRadius + 0.04);
      const markerGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.16, 8);
      disposables.push(markerGeo);
      const markerMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
      disposables.push(markerMat);
      const marker = new THREE.Mesh(markerGeo, markerMat);
      marker.position.copy(pos);
      marker.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), pos.clone().normalize());
      groundStationGroup.add(marker);
    });
    groundStationGroup.visible = layers.groundStations;

    // 7. Orbital Paths & Satellites Group (Requirement 5: PARENTED TO earthGroup so they rotate with Earth!)
    const orbitGroup = new THREE.Group();
    earthGroup.add(orbitGroup);

    interface SatVisualItem {
      id: string;
      mesh: THREE.Group;
      orbitRadius: number;
      inc: number;
      speed: number;
      angle: number;
      orbitLine: THREE.Line;
      reticle: THREE.Mesh;
    }

    const satVisuals: SatVisualItem[] = [];
    const interactiveMeshes: THREE.Object3D[] = [];

    // Redesigned Spacecraft & Clickable Hit Targets (Requirement 6)
    SATELLITE_DIRECTORY.forEach((sat, idx) => {
      const orbitR = earthRadius + 0.9 + (sat.altitudeKm / 800) * 0.9;
      const inc = (sat.inclinationDeg - 90) * (Math.PI / 180);

      // Orbital Ring Trajectory
      const ringPts: THREE.Vector3[] = [];
      const ringSegs = 96;
      for (let i = 0; i <= ringSegs; i++) {
        const theta = (i / ringSegs) * Math.PI * 2;
        const x = orbitR * Math.cos(theta);
        const z = orbitR * Math.sin(theta);
        const y = z * Math.sin(inc);
        const zRot = z * Math.cos(inc);
        ringPts.push(new THREE.Vector3(x, y, zRot));
      }
      const ringGeo = new THREE.BufferGeometry().setFromPoints(ringPts);
      disposables.push(ringGeo);

      const isInitiallySelected = selectedSat.id === sat.id;
      const ringMat = new THREE.LineBasicMaterial({
        color: isInitiallySelected ? 0x00ffff : 0x1a3350,
        transparent: true,
        opacity: isInitiallySelected ? 0.95 : 0.2,
      });
      disposables.push(ringMat);
      const orbitLine = new THREE.Line(ringGeo, ringMat);
      orbitGroup.add(orbitLine);

      // High-Fidelity Spacecraft Model (Requirement 6 redesign)
      const satMesh = new THREE.Group();
      satMesh.userData = { sat };
      if (mode === 'cinematic') {
        satMesh.scale.setScalar(0.78);
      }

      // A. Central Avionics Bus with Gold Foil Thermal Blanket
      const busGeo = new THREE.BoxGeometry(0.42, 0.32, 0.46);
      disposables.push(busGeo);
      const busMat = new THREE.MeshStandardMaterial({
        color: 0xd4af37,
        metalness: 0.88,
        roughness: 0.22,
        emissive: 0x443000,
        emissiveIntensity: 0.4,
      });
      disposables.push(busMat);
      const bus = new THREE.Mesh(busGeo, busMat);
      satMesh.add(bus);

      // B. Dual High-Efficiency Solar Array Wings
      const wingGeo = new THREE.BoxGeometry(1.65, 0.035, 0.44);
      disposables.push(wingGeo);
      const wingMat = new THREE.MeshStandardMaterial({
        color: 0x072b54,
        emissive: 0x0055aa,
        emissiveIntensity: 0.55,
        metalness: 0.7,
        roughness: 0.2,
      });
      disposables.push(wingMat);
      const wings = new THREE.Mesh(wingGeo, wingMat);
      satMesh.add(wings);

      // Wing hinge bracket
      const bracketGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.5, 8);
      disposables.push(bracketGeo);
      const bracketMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.9, roughness: 0.2 });
      disposables.push(bracketMat);
      const bracket = new THREE.Mesh(bracketGeo, bracketMat);
      bracket.rotation.z = Math.PI / 2;
      satMesh.add(bracket);

      // C. Parabolic High-Gain Dish Antenna
      const dishGeo = new THREE.SphereGeometry(0.18, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.45);
      disposables.push(dishGeo);
      const dishMat = new THREE.MeshStandardMaterial({
        color: 0xe2e8f0,
        metalness: 0.85,
        roughness: 0.25,
        side: THREE.DoubleSide,
      });
      disposables.push(dishMat);
      const dish = new THREE.Mesh(dishGeo, dishMat);
      dish.position.set(0, -0.22, 0);
      dish.rotation.x = Math.PI;
      satMesh.add(dish);

      // D. Optical Beacon LED on top
      const beaconColor = sat.status === 'CRITICAL' ? 0xff2244 : sat.status === 'WARNING' ? 0xf59e0b : 0x00e5ff;
      const beaconGeo = new THREE.SphereGeometry(0.09, 12, 12);
      disposables.push(beaconGeo);
      const beaconMat = new THREE.MeshStandardMaterial({
        color: beaconColor,
        emissive: beaconColor,
        emissiveIntensity: 1.5,
        roughness: 0.1,
      });
      disposables.push(beaconMat);
      const beacon = new THREE.Mesh(beaconGeo, beaconMat);
      beacon.position.set(0, 0.22, 0);
      satMesh.add(beacon);

      // E. Selection Reticle Halo
      const reticleGeo = new THREE.RingGeometry(0.55, 0.65, 32);
      disposables.push(reticleGeo);
      const reticleMat = new THREE.MeshBasicMaterial({
        color: 0x00ffff,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.9,
      });
      disposables.push(reticleMat);
      const reticle = new THREE.Mesh(reticleGeo, reticleMat);
      reticle.visible = isInitiallySelected;
      satMesh.add(reticle);

      // F. Generous Invisible Raycast Hit Sphere (Radius 0.72) for effortless clicking
      const hitGeo = new THREE.SphereGeometry(0.72, 12, 12);
      disposables.push(hitGeo);
      const hitMat = new THREE.MeshBasicMaterial({ visible: false });
      disposables.push(hitMat);
      const hitMesh = new THREE.Mesh(hitGeo, hitMat);
      hitMesh.userData = { sat, reticle };
      satMesh.add(hitMesh);
      interactiveMeshes.push(hitMesh);

      // Add spacecraft to orbitGroup
      orbitGroup.add(satMesh);

      satVisuals.push({
        id: sat.id,
        mesh: satMesh,
        orbitRadius: orbitR,
        inc,
        speed: 0.005 + idx * 0.001,
        angle: (idx * Math.PI) / 2.5,
        orbitLine,
        reticle,
      });
    });

    orbitGroup.visible = layers.orbitPaths;

    // 8. Load the single 3D earth_globe.glb model
    earthModelLoader
      .loadEarthModel(earthRadius, (percent) => {
        if (isSubscribed) setLoadPercent(percent);
      })
      .then((result) => {
        if (!isSubscribed) return;
        setIsLoading(false);
        setIsUsingFallback(result.isFallback);
        earthGroup.add(result.scene);
      })
      .catch((err) => {
        console.warn('Failed to load earth_globe.glb, using procedural fallback:', err);
        if (isSubscribed) {
          const fallback = earthModelLoader.createProceduralFallback(earthRadius);
          earthGroup.add(fallback.scene);
          setIsLoading(false);
          setIsUsingFallback(true);
        }
      });

    // 9. Interactive Raycasting & Click Navigation (Requirement 6)
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerDown = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes, true);

      if (intersects.length > 0) {
        let root: THREE.Object3D | null = intersects[0].object;
        while (root && (!root.userData || !root.userData.sat) && root.parent) {
          root = root.parent;
        }

        if (root && root.userData && root.userData.sat) {
          const satData = root.userData.sat as SatelliteMetadata;

          // Requirement 6: If user clicks the already-selected satellite, redirect to dashboard showing its info!
          if (selectedSatRef.current && selectedSatRef.current.id === satData.id) {
            navigate(`/dashboard?satellite=${satData.id}`);
            return;
          }

          // First click: select satellite, only its orbit line glows, other orbit lines dim
          selectedSatRef.current = satData;
          setSelectedSat(satData);
          setIsInfoOpen(true);
          if (onSelectSatellite) onSelectSatellite(satData);

          // Update orbit lines and selection halos
          satVisuals.forEach((item) => {
            const isTarget = item.id === satData.id;
            const lineMat = item.orbitLine.material as THREE.LineBasicMaterial;
            lineMat.color.setHex(isTarget ? 0x00ffff : 0x162c46);
            lineMat.opacity = isTarget ? 0.95 : 0.15;
            lineMat.needsUpdate = true;
            if (item.reticle) {
              item.reticle.visible = isTarget;
            }
          });
        }
      }
    };

    // Hover cursor feedback
    const handlePointerMove = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes, true);
      renderer.domElement.style.cursor = intersects.length > 0 ? 'pointer' : 'grab';
    };

    renderer.domElement.addEventListener('click', handlePointerDown);
    renderer.domElement.addEventListener('mousemove', handlePointerMove);

    // 10. Smooth Drag Orbit Controls (Requirement 2: Strictly constrained to X axis only!)
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      isDragging = true;
      prevMouse = { x: e.clientX, y: e.clientY };
      renderer.domElement.style.cursor = 'grabbing';
    };

    const handleMouseMoveDrag = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouse.x;

      // Requirement 2: Earth movable strictly in X axis (horizontal mouse movement rotates around Y polar axis)
      earthGroup.rotation.y += deltaX * 0.0055;
      earthGroup.rotation.x = 0; // Strictly locked to 0
      earthGroup.rotation.z = 0; // Strictly locked to 0

      // Keep position strictly locked
      earthGroup.position.set(earthPosX, earthPosY, 0);

      prevMouse = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDragging = false;
      renderer.domElement.style.cursor = 'grab';
    };

    // Requirement 9: Scroll wheel zooms ONLY when hovering directly over Earth or satellites!
    const handleWheel = (e: WheelEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event ? e.clientY : 0) - rect.top) / rect.height * -2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects([earthGroup, ...interactiveMeshes], true);

      // If mouse is not directly hovering over Earth or satellites, do NOT preventDefault -> allow page scroll!
      if (hits.length === 0) {
        return;
      }

      e.preventDefault();
      const zoomDelta = e.deltaY * 0.01;
      camera.position.z = Math.max(6.5, Math.min(22, camera.position.z + zoomDelta));
    };

    renderer.domElement.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMoveDrag);
    window.addEventListener('mouseup', handleMouseUp);
    renderer.domElement.addEventListener('wheel', handleWheel, { passive: false });

    // 11. Animation Loop
    let animId = 0;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      // Update twinkling stars uniform
      starUniforms.uTime.value = elapsedTime;

      // Earth auto-rotation strictly around Y axis when not dragging
      if (isRotating && !isDragging) {
        earthGroup.rotation.y += 0.065 * delta;
      }
      earthGroup.rotation.x = 0;
      earthGroup.rotation.z = 0;
      earthGroup.position.set(earthPosX, earthPosY, 0);

      // Satellites along orbits (Requirement 5: orbiting in orbitGroup which rotates with Earth!)
      satVisuals.forEach((sat) => {
        sat.angle += sat.speed;
        const x = sat.orbitRadius * Math.cos(sat.angle);
        const z = sat.orbitRadius * Math.sin(sat.angle);
        const y = z * Math.sin(sat.inc);
        const zRot = z * Math.cos(sat.inc);

        sat.mesh.position.set(x, y, zRot);
        sat.mesh.lookAt(0, 0, 0);

        if (sat.reticle && sat.reticle.visible) {
          sat.reticle.rotation.z += 0.03;
        }
      });

      // Subtle celestial background parallax
      starFieldA.rotation.y += 0.002 * delta;
      navStarField.rotation.y += 0.002 * delta;

      renderer.render(scene, camera);
    };

    animate();

    threeRef.current = {
      renderer,
      scene,
      camera,
      earthGroup,
      orbitGroup,
      groundStationGroup,
      atmosphereMesh,
      satVisuals,
      animId,
      disposables,
    };

    // 12. Responsive Resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = currentHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      isSubscribed = false;
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMoveDrag);
      window.removeEventListener('mouseup', handleMouseUp);
      renderer.domElement.removeEventListener('click', handlePointerDown);
      renderer.domElement.removeEventListener('mousemove', handlePointerMove);
      renderer.domElement.removeEventListener('mousedown', handleMouseDown);
      renderer.domElement.removeEventListener('wheel', handleWheel);

      disposables.forEach((d) => d.dispose());
      renderer.dispose();
      container.innerHTML = '';
    };
  }, [mode, height, isRotating, layers, latLonToVector3, onSelectSatellite, selectedSat.id, navigate]);

  // Viewport quick actions
  const handleZoom = (delta: number) => {
    if (!threeRef.current) return;
    const { camera } = threeRef.current;
    camera.position.z = Math.max(6.5, Math.min(22, camera.position.z + delta));
  };

  const handleResetCamera = () => {
    if (!threeRef.current) return;
    const { camera, earthGroup } = threeRef.current;
    const earthPosX = mode === 'cinematic' ? 2.9 : 0;
    const earthPosY = mode === 'cinematic' ? 0.25 : 0.8;
    camera.position.set(0, mode === 'cinematic' ? 0.2 : 1.2, mode === 'cinematic' ? 11.8 : 12.8);
    earthGroup.rotation.set(0, 0, 0);
    earthGroup.position.set(earthPosX, earthPosY, 0);
  };

  const handleFocusSelected = () => {
    if (!threeRef.current) return;
    const sat = threeRef.current.satVisuals.find((s) => s.id === selectedSat.id);
    if (sat) {
      threeRef.current.camera.lookAt(sat.mesh.position);
    }
  };

  return (
    <div className={`relative w-full rounded sat-panel overflow-hidden border border-[#162744] ${className}`}>
      {/* 3D Canvas Mount */}
      <div ref={mountRef} className="w-full" style={{ height: `${height}px` }} />

      {/* Model Loading State Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-[#030611]/85 backdrop-blur-md flex flex-col items-center justify-center z-40">
          <div className="w-48 bg-[#091224] rounded-full h-2 border border-cyan-500/30 overflow-hidden mb-3">
            <div
              className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300"
              style={{ width: `${loadPercent}%` }}
            />
          </div>
          <span className="font-mono text-xs text-cyan-300 tracking-wider uppercase">
            Loading High-Res Earth Digital Twin ({loadPercent}%)
          </span>
          <span className="text-[10px] font-mono text-slate-500 mt-1">Unpacking earth_globe.glb 66MB asset</span>
        </div>
      )}

      {/* Fallback Notice if GLB failed */}
      {isUsingFallback && !isLoading && (
        <div className="absolute top-3 left-3 z-30 px-2.5 py-1 rounded bg-amber-950/80 border border-amber-500/40 text-[10px] font-mono text-amber-300">
          Earth Texture Mode: Procedural Fallback Active
        </div>
      )}

      {/* UI Overlay Controls (Shown in Dashboard & Fleet views) */}
      {showUIOverlay && (
        <>
          {/* Top Control Header */}
          <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-20">
            <div className="flex items-center gap-2 pointer-events-auto">
              <div className="px-2.5 py-1 rounded bg-[#091224]/85 border border-cyan-500/40 backdrop-blur-md flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-cyan-400" />
                <span className="font-mono text-xs text-slate-200 font-semibold uppercase">
                  {selectedSat.name}
                </span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-bold ${
                    selectedSat.status === 'CRITICAL'
                      ? 'bg-red-950 text-red-300 border border-red-800'
                      : selectedSat.status === 'WARNING'
                      ? 'bg-amber-950 text-amber-300 border border-amber-800'
                      : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  }`}
                >
                  {selectedSat.status}
                </span>
              </div>

              <button
                onClick={() => setIsLayersOpen(!isLayersOpen)}
                className="px-2.5 py-1 rounded bg-[#091224]/85 border border-[#1E355B] hover:border-cyan-400 text-slate-300 hover:text-white backdrop-blur-md flex items-center gap-1.5 text-xs font-mono transition-colors cursor-pointer"
              >
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Layers</span>
              </button>
            </div>

            {/* Viewport Control Actions */}
            <div className="flex items-center gap-1.5 pointer-events-auto">
              <button
                onClick={() => setIsRotating(!isRotating)}
                className="p-1.5 rounded bg-[#091224]/85 border border-[#1E355B] text-slate-300 hover:text-cyan-300 backdrop-blur-md transition-colors cursor-pointer"
                title={isRotating ? 'Pause rotation' : 'Resume rotation'}
              >
                {isRotating ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={() => handleZoom(-1.5)}
                className="p-1.5 rounded bg-[#091224]/85 border border-[#1E355B] text-slate-300 hover:text-cyan-300 backdrop-blur-md transition-colors cursor-pointer"
                title="Zoom in"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleZoom(1.5)}
                className="p-1.5 rounded bg-[#091224]/85 border border-[#1E355B] text-slate-300 hover:text-cyan-300 backdrop-blur-md transition-colors cursor-pointer"
                title="Zoom out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleFocusSelected}
                className="p-1.5 rounded bg-[#091224]/85 border border-[#1E355B] text-slate-300 hover:text-cyan-300 backdrop-blur-md transition-colors cursor-pointer"
                title="Focus Selected Target"
              >
                <Compass className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleResetCamera}
                className="p-1.5 rounded bg-[#091224]/85 border border-[#1E355B] text-slate-300 hover:text-cyan-300 backdrop-blur-md transition-colors cursor-pointer"
                title="Reset orientation"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsInfoOpen(!isInfoOpen)}
                className="p-1.5 rounded bg-[#091224]/85 border border-cyan-500/40 text-cyan-300 hover:text-white backdrop-blur-md transition-colors cursor-pointer"
                title="Satellite Details"
              >
                <Info className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Toggleable Layers Drawer */}
          {isLayersOpen && (
            <div className="absolute top-12 left-3 z-30 p-3.5 rounded bg-[#070D1A]/95 border border-cyan-500/30 backdrop-blur-md shadow-2xl w-64 animate-fade-in text-xs font-mono">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#14233D]">
                <span className="font-semibold text-cyan-300 uppercase tracking-wider">Earth Data Layers</span>
                <button onClick={() => setIsLayersOpen(false)} className="text-slate-500 hover:text-slate-200">
                  &times;
                </button>
              </div>
              <div className="space-y-2.5">
                <label className="flex items-center justify-between text-slate-300 cursor-pointer">
                  <span>Orbital Trajectories</span>
                  <input
                    type="checkbox"
                    checked={layers.orbitPaths}
                    onChange={(e) => setLayers({ ...layers, orbitPaths: e.target.checked })}
                    className="accent-cyan-400"
                  />
                </label>
                <label className="flex items-center justify-between text-slate-300 cursor-pointer">
                  <span>Ground Stations</span>
                  <input
                    type="checkbox"
                    checked={layers.groundStations}
                    onChange={(e) => setLayers({ ...layers, groundStations: e.target.checked })}
                    className="accent-cyan-400"
                  />
                </label>
                <label className="flex items-center justify-between text-slate-300 cursor-pointer">
                  <span>Atmospheric Glow Rim</span>
                  <input
                    type="checkbox"
                    checked={layers.atmosphereGlow}
                    onChange={(e) => setLayers({ ...layers, atmosphereGlow: e.target.checked })}
                    className="accent-cyan-400"
                  />
                </label>
              </div>
            </div>
          )}

          {/* Selected Satellite Info Drawer */}
          {isInfoOpen && (
            <div className="absolute bottom-3 right-3 z-30 p-4 rounded bg-[#070D1A]/95 border border-cyan-500/30 backdrop-blur-md shadow-2xl max-w-sm w-full animate-fade-in text-xs font-mono">
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#14233D]">
                <div>
                  <h4 className="font-display font-semibold text-sm text-slate-100">{selectedSat.name}</h4>
                  <span className="text-[10px] text-cyan-400">NORAD ID: {selectedSat.noradId}</span>
                </div>
                <button onClick={() => setIsInfoOpen(false)} className="text-slate-400 hover:text-white text-base">
                  &times;
                </button>
              </div>

              <div className="space-y-2 mb-4 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Operating Country:</span>
                  <span className="text-slate-100 font-semibold">{selectedSat.operatingCountry}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Operator:</span>
                  <span className="text-slate-200">{selectedSat.operator}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Sub-Satellite Ground Track:</span>
                  <span className="text-cyan-300 text-right">{selectedSat.currentSubpoint.geographicRegion}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Sub-point Coordinates:</span>
                  <span className="text-slate-200">
                    {selectedSat.currentSubpoint.lat}° N, {selectedSat.currentSubpoint.lon}° E
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Altitude / Orbit:</span>
                  <span className="text-slate-200">
                    {selectedSat.altitudeKm} km ({selectedSat.orbitType})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Data Provenance:</span>
                  <span
                    className={
                      selectedSat.dataSource === 'LIVE_BACKEND_STREAM'
                        ? 'text-emerald-400 font-semibold'
                        : 'text-amber-400'
                    }
                  >
                    {selectedSat.dataSource === 'LIVE_BACKEND_STREAM' ? 'LIVE FASTAPI STREAM' : 'SIMULATED PROPAGATION'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-[#14233D]">
                <button
                  onClick={() => navigate('/spacecraft')}
                  className="flex-1 py-2 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 text-cyan-200 text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Inspect 3D Spacecraft</span>
                </button>
                <button
                  onClick={() => navigate(`/dashboard?satellite=${selectedSat.id}`)}
                  className="px-3 py-2 rounded bg-[#0A162C] hover:bg-[#122344] border border-[#1F365E] text-slate-300 text-[11px] transition-colors cursor-pointer"
                >
                  Telemetry &rarr;
                </button>
              </div>
            </div>
          )}

          {/* Bottom Sub-point Status Banner */}
          <div className="absolute bottom-2 left-3 pointer-events-none flex items-center gap-2 font-mono text-[10px] text-slate-400 bg-[#060D1C]/80 px-2.5 py-1 rounded border border-[#162744]">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span>GROUND TRACK:</span>
            <span className="text-slate-200">{selectedSat.currentSubpoint.geographicRegion}</span>
            <span className="text-slate-500">|</span>
            <span>LAT: {selectedSat.currentSubpoint.lat}°</span>
            <span>LON: {selectedSat.currentSubpoint.lon}°</span>
          </div>
        </>
      )}
    </div>
  );
};

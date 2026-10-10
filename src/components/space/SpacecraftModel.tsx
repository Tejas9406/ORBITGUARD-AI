import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

export type SubsystemKey = 'EPS' | 'TCS' | 'AOCS' | 'TTC' | 'OBC' | 'SENSORS';

interface SpacecraftModelProps {
  selectedSubsystem: SubsystemKey;
  onSelectSubsystem: (key: SubsystemKey) => void;
  activeAnomalySubsystem?: SubsystemKey | null;
  className?: string;
  height?: number;
}

export const SpacecraftModel: React.FC<SpacecraftModelProps> = ({
  selectedSubsystem,
  onSelectSubsystem,
  activeAnomalySubsystem,
  className = '',
  height = 520,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [hoveredSubsystem, setHoveredSubsystem] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // References for Three.js state
  const threeRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    group: THREE.Group;
    meshes: Map<SubsystemKey, THREE.Mesh[]>;
    animId: number;
    disposables: { dispose: () => void }[];
  } | null>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    let isSubscribed = true;
    const width = container.clientWidth || 800;
    const currentHeight = height;

    const disposables: { dispose: () => void }[] = [];

    // Scene & Camera
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x030713);

    const camera = new THREE.PerspectiveCamera(40, width / currentHeight, 0.1, 1000);
    camera.position.set(7.5, 4.2, 8.5);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, currentHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Deep space lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff7ea, 2.2);
    keyLight.position.set(10, 12, 10);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x00e5ff, 0.85);
    fillLight.position.set(-12, -6, -8);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 1.1);
    rimLight.position.set(0, -8, 6);
    scene.add(rimLight);

    // Deep Space Star particles
    const starGeo = new THREE.BufferGeometry();
    disposables.push(starGeo);
    const starCount = 500;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPos[i] = (Math.random() - 0.5) * 90;
      starPos[i + 1] = (Math.random() - 0.5) * 90;
      starPos[i + 2] = (Math.random() - 0.5) * 90;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: 0x77bbee, size: 0.12, transparent: true, opacity: 0.7 });
    disposables.push(starMat);
    scene.add(new THREE.Points(starGeo, starMat));

    // Spacecraft Master Group
    const spacecraftGroup = new THREE.Group();
    scene.add(spacecraftGroup);

    // Subsystem mesh dictionary
    const subsystemMeshes = new Map<SubsystemKey, THREE.Mesh[]>();
    const interactiveMeshes: THREE.Object3D[] = [];

    const registerMesh = (key: SubsystemKey, mesh: THREE.Mesh) => {
      mesh.userData = { subsystemKey: key };
      interactiveMeshes.push(mesh);
      if (!subsystemMeshes.has(key)) {
        subsystemMeshes.set(key, []);
      }
      subsystemMeshes.get(key)!.push(mesh);
    };

    // Load the official Apollo Soyuz.glb model (Requirement 8)
    const loader = new GLTFLoader();
    const modelUrl = '/apollo_soyuz.glb';

    loader.load(
      modelUrl,
      (gltf) => {
        if (!isSubscribed) return;
        setIsLoading(false);

        const model = gltf.scene;

        // Compute bounds and center
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const targetScale = 7.2 / maxDim;

        const modelWrapper = new THREE.Group();
        // Center geometry
        model.position.set(-center.x, -center.y, -center.z);
        modelWrapper.scale.setScalar(targetScale);
        modelWrapper.add(model);
        spacecraftGroup.add(modelWrapper);

        // Map Apollo-Soyuz meshes to the 6 Subsystems
        model.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            // Clone material so subsystem emissive highlights don't affect shared instances
            if (mesh.material) {
              const origMat = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
              const clonedMat = origMat.clone() as THREE.MeshStandardMaterial;
              clonedMat.roughness = Math.min(clonedMat.roughness ?? 0.5, 0.45);
              clonedMat.metalness = Math.max(clonedMat.metalness ?? 0.5, 0.65);
              mesh.material = clonedMat;
              mesh.userData.originalEmissive = clonedMat.emissive ? clonedMat.emissive.clone() : new THREE.Color(0x000000);
              mesh.userData.originalEmissiveIntensity = clonedMat.emissiveIntensity ?? 0;
            }

            const name = mesh.name;
            // Map meshes based on anatomical structure:
            // polySurfac_4, 6: Soyuz Solar Array Wings -> EPS
            if (name.includes('polySurfac_4') || name.includes('polySurfac_6')) {
              registerMesh('EPS', mesh);
            }
            // polySurfac_13, 17: Apollo Service Module Cylinder & Radiators -> TCS
            else if (name.includes('polySurfac_13') || name.includes('polySurfac_17')) {
              registerMesh('TCS', mesh);
            }
            // polySurfac_14, 16: Apollo Command Module & SPS Propulsion Nozzle -> AOCS
            else if (name.includes('polySurfac_14') || name.includes('polySurfac_16')) {
              registerMesh('AOCS', mesh);
            }
            // polySurfac_10, 12: Docking Module & VHF Communications -> TTC
            else if (name.includes('polySurfac_10') || name.includes('polySurfac_12')) {
              registerMesh('TTC', mesh);
            }
            // polySurfac_1, 3, 5: Soyuz Orbital & Instrument Modules -> OBC
            else if (name.includes('polySurfac_1') || name.includes('polySurfac_3') || name.includes('polySurfac_5')) {
              registerMesh('OBC', mesh);
            }
            // polySurfac_2, 7, 8, 9, 11, 15, 18: Optical Alignment Target, Periscopes, Sensors -> SENSORS
            else {
              registerMesh('SENSORS', mesh);
            }
          }
        });
      },
      undefined,
      (error) => {
        console.warn('Failed to load apollo_soyuz.glb, activating procedural fallback:', error);
        if (!isSubscribed) return;
        setIsLoading(false);
        buildProceduralFallback(spacecraftGroup, disposables, registerMesh);
      }
    );

    // Raycasting for Mouse Hover and Click
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes, true);
      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && (!obj.userData || !obj.userData.subsystemKey) && obj.parent) {
          obj = obj.parent;
        }
        if (obj && obj.userData && obj.userData.subsystemKey) {
          const key = obj.userData.subsystemKey as SubsystemKey;
          setHoveredSubsystem(key);
          container.style.cursor = 'pointer';
          return;
        }
      }
      setHoveredSubsystem(null);
      container.style.cursor = isDragging ? 'grabbing' : 'grab';
    };

    const handlePointerClick = () => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes, true);
      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && (!obj.userData || !obj.userData.subsystemKey) && obj.parent) {
          obj = obj.parent;
        }
        if (obj && obj.userData && obj.userData.subsystemKey) {
          const key = obj.userData.subsystemKey as SubsystemKey;
          onSelectSubsystem(key);
        }
      }
    };

    renderer.domElement.addEventListener('mousemove', handlePointerMove);
    renderer.domElement.addEventListener('click', handlePointerClick);

    // Orbit & Drag rotation controls
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      isDragging = true;
      prevMouse = { x: e.clientX, y: e.clientY };
      container.style.cursor = 'grabbing';
    };

    const handleMouseMoveDrag = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouse.x;
      const deltaY = e.clientY - prevMouse.y;
      spacecraftGroup.rotation.y += deltaX * 0.007;
      spacecraftGroup.rotation.x += deltaY * 0.007;
      prevMouse = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDragging = false;
      container.style.cursor = 'grab';
    };

    // Zoom via wheel
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomDelta = e.deltaY * 0.01;
      camera.position.z = Math.max(5.0, Math.min(18.0, camera.position.z + zoomDelta));
    };

    renderer.domElement.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMoveDrag);
    window.addEventListener('mouseup', handleMouseUp);
    renderer.domElement.addEventListener('wheel', handleWheel, { passive: false });

    // Animation Loop
    let animId = 0;
    const animate = () => {
      animId = requestAnimationFrame(animate);

      // Idle gentle float
      if (!isDragging) {
        spacecraftGroup.rotation.y += 0.0025;
      }

      // Highlight selected or anomaly subsystem meshes
      subsystemMeshes.forEach((meshes, key) => {
        const isSelected = selectedSubsystem === key;
        const isAnomaly = activeAnomalySubsystem === key;
        const isHovered = hoveredSubsystem === key;

        meshes.forEach((m) => {
          const mat = m.material as THREE.MeshStandardMaterial;
          if (!mat || !mat.emissive) return;

          if (isAnomaly) {
            mat.emissive.setHex(0xef4444);
            mat.emissiveIntensity = 0.9 + Math.sin(Date.now() * 0.008) * 0.4;
          } else if (isSelected) {
            mat.emissive.setHex(0x00e5ff);
            mat.emissiveIntensity = 0.8 + Math.sin(Date.now() * 0.006) * 0.25;
          } else if (isHovered) {
            mat.emissive.setHex(0x38bdf8);
            mat.emissiveIntensity = 0.6;
          } else {
            const origEmissive = m.userData.originalEmissive as THREE.Color | undefined;
            const origIntensity = (m.userData.originalEmissiveIntensity as number) ?? 0;
            if (origEmissive) {
              mat.emissive.copy(origEmissive);
              mat.emissiveIntensity = origIntensity;
            } else {
              mat.emissive.setHex(0x000000);
              mat.emissiveIntensity = 0;
            }
          }
        });
      });

      renderer.render(scene, camera);
    };

    animate();

    threeRef.current = {
      renderer,
      scene,
      camera,
      group: spacecraftGroup,
      meshes: subsystemMeshes,
      animId,
      disposables,
    };

    // Responsive Resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = currentHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      isSubscribed = false;
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMoveDrag);
      window.removeEventListener('mouseup', handleMouseUp);
      renderer.domElement.removeEventListener('mousemove', handlePointerMove);
      renderer.domElement.removeEventListener('click', handlePointerClick);
      renderer.domElement.removeEventListener('mousedown', handleMouseDown);
      renderer.domElement.removeEventListener('wheel', handleWheel);

      disposables.forEach((d) => d.dispose());
      renderer.dispose();
      container.innerHTML = '';
    };
  }, [height, selectedSubsystem, activeAnomalySubsystem, hoveredSubsystem, onSelectSubsystem]);

  return (
    <div className={`relative w-full rounded sat-panel overflow-hidden border border-[#162744] ${className}`}>
      <div ref={mountRef} className="w-full" style={{ height: `${height}px` }} />

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-[#030611]/85 backdrop-blur-md flex flex-col items-center justify-center z-40">
          <div className="w-48 bg-[#091224] rounded-full h-2 border border-cyan-500/30 overflow-hidden mb-3">
            <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full w-2/3 animate-pulse" />
          </div>
          <span className="font-mono text-xs text-cyan-300 tracking-wider uppercase">
            Loading Apollo-Soyuz 3D Digital Twin
          </span>
          <span className="text-[10px] font-mono text-slate-500 mt-1">Unpacking Apollo Soyuz.glb CAD Assembly</span>
        </div>
      )}

      {/* Hovered Subsystem HUD tooltip */}
      {hoveredSubsystem && (
        <div className="absolute top-4 left-4 z-20 px-3 py-1.5 rounded bg-[#091224]/90 border border-cyan-400/50 backdrop-blur-md text-xs font-mono text-cyan-300 pointer-events-none animate-fade-in flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>Subsystem Target: <strong className="text-white uppercase">{hoveredSubsystem}</strong></span>
          <span className="text-slate-500">•</span>
          <span className="text-[10px] text-slate-400">Click to inspect</span>
        </div>
      )}

      {/* Viewport Control Instructions */}
      <div className="absolute bottom-3 left-3 z-20 text-[10px] font-mono text-slate-400 pointer-events-none bg-[#030713]/70 px-2.5 py-1 rounded border border-[#142340]">
        <span>Left Drag: 3D Rotate</span>
        <span className="mx-2">•</span>
        <span>Scroll: Zoom</span>
        <span className="mx-2">•</span>
        <span>Click: Subsystem Diagnostics</span>
      </div>
    </div>
  );
};

// Procedural fallback if GLTF asset load fails
function buildProceduralFallback(
  spacecraftGroup: THREE.Group,
  disposables: { dispose: () => void }[],
  registerMesh: (key: SubsystemKey, mesh: THREE.Mesh) => void
) {
  const busGeo = new THREE.BoxGeometry(2.0, 2.6, 2.0);
  disposables.push(busGeo);
  const busMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.85, roughness: 0.25 });
  disposables.push(busMat);
  const bus = new THREE.Mesh(busGeo, busMat);
  spacecraftGroup.add(bus);

  const wingGeo = new THREE.BoxGeometry(4.2, 0.05, 1.4);
  disposables.push(wingGeo);
  const wingMat = new THREE.MeshStandardMaterial({ color: 0x052244, emissive: 0x004488, emissiveIntensity: 0.5 });
  disposables.push(wingMat);
  const portWing = new THREE.Mesh(wingGeo, wingMat.clone());
  portWing.position.set(3.2, 0, 0);
  spacecraftGroup.add(portWing);
  registerMesh('EPS', portWing);

  const stbdWing = new THREE.Mesh(wingGeo, wingMat.clone());
  stbdWing.position.set(-3.2, 0, 0);
  spacecraftGroup.add(stbdWing);
  registerMesh('EPS', stbdWing);

  const radGeo = new THREE.BoxGeometry(1.6, 0.1, 1.6);
  disposables.push(radGeo);
  const radMat = new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.9, roughness: 0.15 });
  disposables.push(radMat);
  const radTop = new THREE.Mesh(radGeo, radMat);
  radTop.position.set(0, 1.35, 0);
  spacecraftGroup.add(radTop);
  registerMesh('TCS', radTop);

  const wheelGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.25, 24);
  disposables.push(wheelGeo);
  const wheelMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, metalness: 0.8, roughness: 0.25 });
  disposables.push(wheelMat);
  const wheel = new THREE.Mesh(wheelGeo, wheelMat);
  wheel.position.set(0, 0, 1.1);
  wheel.rotation.x = Math.PI / 2;
  spacecraftGroup.add(wheel);
  registerMesh('AOCS', wheel);
}

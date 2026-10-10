import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { clone as skeletonClone } from 'three/examples/jsm/utils/SkeletonUtils.js';

export interface EarthModelLoadResult {
  scene: THREE.Group;
  originalRadius: number;
  center: THREE.Vector3;
  meshCount: number;
  isFallback: boolean;
}

class EarthModelLoader {
  private static instance: EarthModelLoader;
  private cachedGltfScene: THREE.Group | null = null;
  private cachedBounds: { center: THREE.Vector3; size: THREE.Vector3; radius: number } | null = null;
  private loadPromise: Promise<EarthModelLoadResult> | null = null;

  public static getInstance(): EarthModelLoader {
    if (!EarthModelLoader.instance) {
      EarthModelLoader.instance = new EarthModelLoader();
    }
    return EarthModelLoader.instance;
  }

  /**
   * Asynchronously loads and caches the 66MB earth_globe.glb model.
   * Subsequent calls reuse the cached template and return a cloned Three.js Group.
   */
  public loadEarthModel(
    targetRadius: number = 3.8,
    onProgress?: (percent: number) => void
  ): Promise<EarthModelLoadResult> {
    // If already loaded and cached, return an instantly cloned scene
    if (this.cachedGltfScene && this.cachedBounds) {
      if (onProgress) onProgress(100);
      const cloned = this.instantiateModel(this.cachedGltfScene, this.cachedBounds, targetRadius);
      return Promise.resolve({
        scene: cloned,
        originalRadius: this.cachedBounds.radius,
        center: this.cachedBounds.center.clone(),
        meshCount: 3,
        isFallback: false,
      });
    }

    // If currently loading in another component, share the in-flight Promise
    if (this.loadPromise) {
      return this.loadPromise.then((res) => {
        if (this.cachedGltfScene && this.cachedBounds) {
          const cloned = this.instantiateModel(this.cachedGltfScene, this.cachedBounds, targetRadius);
          return {
            ...res,
            scene: cloned,
          };
        }
        return res;
      });
    }

    this.loadPromise = new Promise<EarthModelLoadResult>((resolve) => {
      const loader = new GLTFLoader();
      const modelUrl = '/earth_globe.glb';

      loader.load(
        modelUrl,
        (gltf) => {
          try {
            const rawScene = gltf.scene;

            // Compute precise bounding box and center
            const box = new THREE.Box3().setFromObject(rawScene);
            const size = box.getSize(new THREE.Vector3());
            const center = box.getCenter(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const radius = maxDim / 2;

            // Enhance materials: convert to standard materials if needed so it responds to directional sunlight
            rawScene.traverse((child) => {
              if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                mesh.castShadow = true;
                mesh.receiveShadow = true;

                if (mesh.material) {
                  const origMat = mesh.material as THREE.MeshStandardMaterial;
                  if (origMat.map) {
                    origMat.map.colorSpace = THREE.SRGBColorSpace;
                    origMat.map.generateMipmaps = true;
                    origMat.map.minFilter = THREE.LinearMipmapLinearFilter;
                  }

                  // Use MeshStandardMaterial with original texture maps for vibrant, bright planetary illumination
                  const standardMat = new THREE.MeshStandardMaterial({
                    map: origMat.map || null,
                    normalMap: origMat.normalMap || null,
                    roughnessMap: origMat.roughnessMap || null,
                    roughness: 0.52,
                    metalness: 0.02,
                    emissive: new THREE.Color(0x0a2f58),
                    emissiveIntensity: 0.48,
                  });
                  mesh.material = standardMat;
                }
              }
            });

            this.cachedGltfScene = rawScene;
            this.cachedBounds = { center, size, radius };

            const instantiated = this.instantiateModel(rawScene, this.cachedBounds, targetRadius);
            this.loadPromise = null;

            resolve({
              scene: instantiated,
              originalRadius: radius,
              center,
              meshCount: 3,
              isFallback: false,
            });
          } catch (err) {
            console.warn('[EarthModelLoader] Error processing GLTF scene, using procedural fallback:', err);
            this.loadPromise = null;
            resolve(this.createProceduralFallback(targetRadius));
          }
        },
        (progressEvent) => {
          if (progressEvent.lengthComputable && progressEvent.total > 0 && onProgress) {
            const percent = Math.min(99, Math.round((progressEvent.loaded / progressEvent.total) * 100));
            onProgress(percent);
          }
        },
        (error) => {
          console.warn('[EarthModelLoader] GLTF load failed, activating high-fidelity fallback:', error);
          this.loadPromise = null;
          resolve(this.createProceduralFallback(targetRadius));
        }
      );
    });

    return this.loadPromise;
  }

  /**
   * Centers the model to (0, 0, 0) and scales uniformly to targetRadius.
   */
  private instantiateModel(
    templateScene: THREE.Group,
    bounds: { center: THREE.Vector3; size: THREE.Vector3; radius: number },
    targetRadius: number
  ): THREE.Group {
    const cloned = skeletonClone(templateScene) as THREE.Group;
    const pivot = new THREE.Group();

    // Center the cloned geometry relative to pivot origin (0, 0, 0)
    cloned.position.set(-bounds.center.x, -bounds.center.y, -bounds.center.z);
    cloned.scale.setScalar(1);
    pivot.add(cloned);

    // Correct upside-down GLTF orientation:
    // Flip 180 degrees around X with ~22 deg forward tilt so India & Northern Hemisphere face the user directly
    pivot.rotation.x = Math.PI - 0.38;
    // Rotate around Y to place India dead-center
    pivot.rotation.y = -0.70;

    // Uniformly scale the wrapper so that both model geometry and offset scale together
    const wrapper = new THREE.Group();
    const scaleFactor = targetRadius / bounds.radius;
    wrapper.scale.setScalar(scaleFactor);
    wrapper.add(pivot);

    return wrapper;
  }

  /**
   * Procedural Earth fallback if network or WebGL fails on 66MB asset.
   */
  public createProceduralFallback(targetRadius: number): EarthModelLoadResult {
    const group = new THREE.Group();
    const geo = new THREE.SphereGeometry(targetRadius, 64, 64);

    // Procedural canvas texture
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#061022';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#0F2547';
    // Continents
    ctx.beginPath();
    ctx.ellipse(250, 160, 110, 80, -0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(320, 340, 60, 95, 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(680, 160, 180, 85, 0.1, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(540, 270, 75, 110, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(820, 360, 60, 45, 0, 0, Math.PI * 2);
    ctx.fill();

    const texture = new THREE.CanvasTexture(canvas);
    const mat = new THREE.MeshStandardMaterial({
      map: texture,
      roughness: 0.7,
      metalness: 0.1,
      emissive: new THREE.Color(0x020814),
      emissiveIntensity: 0.4,
    });
    const mesh = new THREE.Mesh(geo, mat);
    group.add(mesh);

    return {
      scene: group,
      originalRadius: targetRadius,
      center: new THREE.Vector3(0, 0, 0),
      meshCount: 1,
      isFallback: true,
    };
  }
}

export const earthModelLoader = EarthModelLoader.getInstance();

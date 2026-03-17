import { useRef, useMemo, useCallback, useEffect, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const DESKTOP_NEURONS = 220;
const MOBILE_NEURONS = 80;
const CONNECTION_DISTANCE = 2.4;
const PULSE_SPEED = 0.8;

function useIsMobile() {
  const [mobile, setMobile] = useState(
    () => typeof window !== "undefined" && window.innerWidth < 768
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return mobile;
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return reduced;
}

/** Glowing neuron particles + dynamic connections + mouse-reactive drift */
function NeuralNetwork({ neuronCount }: { neuronCount: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  const linesRef = useRef<THREE.LineSegments>(null);
  const glowRef = useRef<THREE.Points>(null);
  const groupRef = useRef<THREE.Group>(null);
  const { pointer } = useThree();

  const { positions, velocities, sizes } = useMemo(() => {
    const pos = new Float32Array(neuronCount * 3);
    const vel = new Float32Array(neuronCount * 3);
    const sz = new Float32Array(neuronCount);
    for (let i = 0; i < neuronCount; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 12;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 12;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12;
      vel[i * 3] = (Math.random() - 0.5) * 0.004;
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.004;
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.004;
      sz[i] = 0.04 + Math.random() * 0.06;
    }
    return { positions: pos, velocities: vel, sizes: sz };
  }, [neuronCount]);

  const glowPositions = useMemo(() => new Float32Array(positions), [positions]);

  const linePositions = useMemo(
    () => new Float32Array(neuronCount * neuronCount * 6),
    [neuronCount]
  );
  const lineColors = useMemo(
    () => new Float32Array(neuronCount * neuronCount * 6),
    [neuronCount]
  );

  useFrame(({ clock }) => {
    if (!pointsRef.current || !linesRef.current || !groupRef.current) return;

    const t = clock.getElapsedTime();
    const posAttr = pointsRef.current.geometry.attributes
      .position as THREE.BufferAttribute;
    const sizeAttr = pointsRef.current.geometry.attributes
      .size as THREE.BufferAttribute;
    const arr = posAttr.array as Float32Array;
    const szArr = sizeAttr.array as Float32Array;

    // Move neurons + pulse sizes
    for (let i = 0; i < neuronCount; i++) {
      arr[i * 3] += velocities[i * 3];
      arr[i * 3 + 1] += velocities[i * 3 + 1];
      arr[i * 3 + 2] += velocities[i * 3 + 2];

      for (let d = 0; d < 3; d++) {
        if (Math.abs(arr[i * 3 + d]) > 6) velocities[i * 3 + d] *= -1;
      }

      // Pulsating size
      szArr[i] = sizes[i] * (1 + 0.4 * Math.sin(t * PULSE_SPEED + i * 0.3));
    }
    posAttr.needsUpdate = true;
    sizeAttr.needsUpdate = true;

    // Update glow layer
    if (glowRef.current) {
      const glowAttr = glowRef.current.geometry.attributes
        .position as THREE.BufferAttribute;
      (glowAttr.array as Float32Array).set(arr);
      glowAttr.needsUpdate = true;
    }

    // Build connections with distance-based brightness
    let lineIdx = 0;
    let colorIdx = 0;
    for (let i = 0; i < neuronCount; i++) {
      for (let j = i + 1; j < neuronCount; j++) {
        const dx = arr[i * 3] - arr[j * 3];
        const dy = arr[i * 3 + 1] - arr[j * 3 + 1];
        const dz = arr[i * 3 + 2] - arr[j * 3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist < CONNECTION_DISTANCE) {
          const alpha = 1 - dist / CONNECTION_DISTANCE;
          linePositions[lineIdx++] = arr[i * 3];
          linePositions[lineIdx++] = arr[i * 3 + 1];
          linePositions[lineIdx++] = arr[i * 3 + 2];
          linePositions[lineIdx++] = arr[j * 3];
          linePositions[lineIdx++] = arr[j * 3 + 1];
          linePositions[lineIdx++] = arr[j * 3 + 2];
          const r = 0.15 * alpha;
          const g = 0.39 * alpha;
          const b = 0.92 * alpha;
          lineColors[colorIdx++] = r;
          lineColors[colorIdx++] = g;
          lineColors[colorIdx++] = b;
          lineColors[colorIdx++] = r;
          lineColors[colorIdx++] = g;
          lineColors[colorIdx++] = b;
        }
      }
    }

    const lineGeom = linesRef.current.geometry;
    const linePosAttr = lineGeom.attributes.position as THREE.BufferAttribute;
    (linePosAttr.array as Float32Array).set(linePositions);
    linePosAttr.needsUpdate = true;
    const lineColAttr = lineGeom.attributes.color as THREE.BufferAttribute;
    (lineColAttr.array as Float32Array).set(lineColors);
    lineColAttr.needsUpdate = true;
    lineGeom.setDrawRange(0, lineIdx / 3);

    // Slow rotation + mouse-reactive drift
    const targetX = pointer.y * 0.15;
    const targetY = pointer.x * 0.15;
    groupRef.current.rotation.x +=
      (targetX - groupRef.current.rotation.x) * 0.02;
    groupRef.current.rotation.y +=
      (targetY + t * 0.05 - groupRef.current.rotation.y) * 0.02;
  });

  // Custom shader for variable-size glowing points
  const pointShader = useMemo(
    () => ({
      uniforms: {
        uColor: { value: new THREE.Color("#60a5fa") },
      },
      vertexShader: `
        attribute float size;
        varying float vAlpha;
        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (300.0 / -mvPosition.z);
          gl_Position = projectionMatrix * mvPosition;
          vAlpha = size * 12.0;
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        varying float vAlpha;
        void main() {
          float d = length(gl_PointCoord - vec2(0.5));
          if (d > 0.5) discard;
          float glow = smoothstep(0.5, 0.0, d);
          gl_FragColor = vec4(uColor, glow * clamp(vAlpha, 0.3, 1.0));
        }
      `,
      transparent: true,
      depthWrite: false,
    }),
    []
  );

  return (
    <group ref={groupRef}>
      {/* Core neurons with custom glow shader */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            array={positions}
            count={neuronCount}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-size"
            array={sizes}
            count={neuronCount}
            itemSize={1}
          />
        </bufferGeometry>
        <shaderMaterial attach="material" args={[pointShader]} />
      </points>

      {/* Glow halo layer — larger, additive blending */}
      <points ref={glowRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            array={glowPositions}
            count={neuronCount}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.2}
          color="#3b82f6"
          transparent
          opacity={0.12}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Dynamic connections with vertex colors */}
      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            array={linePositions}
            count={linePositions.length / 3}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            array={lineColors}
            count={lineColors.length / 3}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial vertexColors transparent opacity={0.35} />
      </lineSegments>
    </group>
  );
}

/** Floating ambient orbs for depth */
function AmbientOrbs() {
  const ref1 = useRef<THREE.Mesh>(null);
  const ref2 = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (ref1.current) {
      ref1.current.position.x = Math.sin(t * 0.2) * 4;
      ref1.current.position.y = Math.cos(t * 0.15) * 3;
    }
    if (ref2.current) {
      ref2.current.position.x = Math.cos(t * 0.18) * 3.5;
      ref2.current.position.y = Math.sin(t * 0.22) * 4;
    }
  });

  return (
    <>
      <mesh ref={ref1} position={[-3, 2, -5]}>
        <sphereGeometry args={[1.8, 16, 16]} />
        <meshBasicMaterial color="#1d4ed8" transparent opacity={0.04} />
      </mesh>
      <mesh ref={ref2} position={[3, -2, -4]}>
        <sphereGeometry args={[2.2, 16, 16]} />
        <meshBasicMaterial color="#7c3aed" transparent opacity={0.03} />
      </mesh>
    </>
  );
}

/** Static fallback for reduced-motion users */
function StaticBackground() {
  return (
    <div className="fixed inset-0 -z-10 bg-gray-950">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.08)_0%,transparent_70%)]" />
    </div>
  );
}

export default function NeuralBackground() {
  const isMobile = useIsMobile();
  const prefersReduced = usePrefersReducedMotion();

  const handleCreated = useCallback(({ gl }: { gl: THREE.WebGLRenderer }) => {
    gl.setClearColor("#030712", 1);
  }, []);

  // Show static gradient for reduced-motion preference
  if (prefersReduced) return <StaticBackground />;

  const neuronCount = isMobile ? MOBILE_NEURONS : DESKTOP_NEURONS;
  const maxDpr: [number, number] = isMobile ? [1, 1] : [1, 1.5];

  return (
    <div className="fixed inset-0 -z-10">
      <Canvas
        dpr={maxDpr}
        camera={{ position: [0, 0, 8], fov: 55 }}
        onCreated={handleCreated}
      >
        <NeuralNetwork neuronCount={neuronCount} />
        <AmbientOrbs />
      </Canvas>
    </div>
  );
}

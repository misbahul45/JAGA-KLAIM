"use client";

import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  Group,
  MathUtils,
  Points,
  ShaderMaterial,
  Vector3,
} from "three";
import type { RootState, ThreeEvent } from "@react-three/fiber";

const DOT_COLS = 28;
const DOT_ROWS = 26;
const DOT_COUNT = DOT_COLS * DOT_ROWS;

const COLORS = {
  blue: "#3976b8",
  blueLight: "#8bbce8",
  cyan: "#83cbdc",
  navy: "#173b63",
  slate: "#9db0c4",
  white: "#ffffff",
};

const DOT_VERTEX_SHADER = /* glsl */ `
  uniform float uTime;
  uniform float uPixelRatio;

  attribute float aSeed;
  attribute vec3 aColor;

  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec3 p = position;

    float waveA = sin(p.x * 0.48 + uTime * 0.28 + aSeed * 1.4);
    float waveB = cos(p.y * 0.55 - uTime * 0.22 + aSeed);

    float wave = waveA * 0.55 + waveB * 0.45;

    p.z += wave * 0.18;

    vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);

    float depth = max(1.0, -mvPosition.z);

    gl_Position = projectionMatrix * mvPosition;
    gl_PointSize = clamp(
      (1.7 + aSeed * 1.2) * uPixelRatio * (7.0 / depth),
      1.0,
      5.0
    );

    vColor = aColor;

    float edgeX = 1.0 - smoothstep(2.8, 4.0, abs(p.x));
    float edgeY = 1.0 - smoothstep(2.5, 3.5, abs(p.y));

    vAlpha = (0.24 + (wave * 0.5 + 0.5) * 0.34)
      * edgeX
      * edgeY;
  }
`;

const DOT_FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec2 centered = gl_PointCoord - vec2(0.5);
    float distanceToCenter = length(centered);

    float alpha = 1.0 - smoothstep(0.22, 0.5, distanceToCenter);

    if (alpha < 0.025) discard;

    gl_FragColor = vec4(vColor, alpha * vAlpha);
  }
`;

type Node = {
  id: number;
  position: [number, number, number];
  color: string;
  radius: number;
  phase: number;
};

const GRAPH_NODES: Node[] = [
  {
    id: 0,
    position: [-1.8, 1.05, 0],
    color: COLORS.blue,
    radius: 0.105,
    phase: 0.2,
  },
  {
    id: 1,
    position: [-0.8, 1.75, 0.1],
    color: COLORS.blueLight,
    radius: 0.075,
    phase: 1.1,
  },
  {
    id: 2,
    position: [0.5, 1.35, -0.1],
    color: COLORS.cyan,
    radius: 0.09,
    phase: 2.1,
  },
  {
    id: 3,
    position: [1.65, 0.85, 0.15],
    color: COLORS.blue,
    radius: 0.11,
    phase: 0.7,
  },
  {
    id: 4,
    position: [-1.25, 0.15, 0.2],
    color: COLORS.slate,
    radius: 0.07,
    phase: 1.8,
  },
  {
    id: 5,
    position: [0, 0.25, 0],
    color: COLORS.navy,
    radius: 0.16,
    phase: 0,
  },
  {
    id: 6,
    position: [1.15, -0.1, 0.1],
    color: COLORS.cyan,
    radius: 0.08,
    phase: 2.7,
  },
  {
    id: 7,
    position: [-1.65, -1.0, -0.1],
    color: COLORS.blueLight,
    radius: 0.08,
    phase: 1.4,
  },
  {
    id: 8,
    position: [-0.45, -1.25, 0.1],
    color: COLORS.blue,
    radius: 0.105,
    phase: 2.4,
  },
  {
    id: 9,
    position: [0.75, -1.15, -0.1],
    color: COLORS.slate,
    radius: 0.075,
    phase: 0.9,
  },
  {
    id: 10,
    position: [1.8, -1.0, 0.1],
    color: COLORS.blueLight,
    radius: 0.09,
    phase: 1.9,
  },
];

const GRAPH_EDGES: [number, number][] = [
  [0, 1],
  [1, 2],
  [2, 3],
  [0, 4],
  [1, 5],
  [2, 5],
  [3, 6],
  [4, 5],
  [5, 6],
  [4, 7],
  [4, 8],
  [5, 8],
  [5, 9],
  [6, 9],
  [6, 10],
  [7, 8],
  [8, 9],
  [9, 10],
];

function createDotGeometry() {
  const positions = new Float32Array(DOT_COUNT * 3);
  const seeds = new Float32Array(DOT_COUNT);
  const colors = new Float32Array(DOT_COUNT * 3);

  const palette = [
    new Color(COLORS.blue),
    new Color(COLORS.blueLight),
    new Color(COLORS.cyan),
    new Color(COLORS.slate),
  ];

  let index = 0;

  for (let row = 0; row < DOT_ROWS; row += 1) {
    for (let col = 0; col < DOT_COLS; col += 1) {
      const i = index * 3;

      const x = (col / (DOT_COLS - 1) - 0.5) * 7.5;
      const y = (row / (DOT_ROWS - 1) - 0.5) * 6.2;

      positions[i] = x;
      positions[i + 1] = y;
      positions[i + 2] = -1.4;

      const seed = (
        Math.sin(index * 12.9898) * 43758.5453
      ) % 1;

      const normalizedSeed = Math.abs(seed);

      seeds[index] = normalizedSeed;

      const paletteIndex = Math.min(
        palette.length - 1,
        Math.floor(normalizedSeed * palette.length),
      );

      const color = palette[paletteIndex];

      colors[i] = color.r;
      colors[i + 1] = color.g;
      colors[i + 2] = color.b;

      index += 1;
    }
  }

  const geometry = new BufferGeometry();

  geometry.setAttribute(
    "position",
    new BufferAttribute(positions, 3),
  );

  geometry.setAttribute(
    "aSeed",
    new BufferAttribute(seeds, 1),
  );

  geometry.setAttribute(
    "aColor",
    new BufferAttribute(colors, 3),
  );

  return geometry;
}

function createEdgeGeometry() {
  const positions: number[] = [];

  for (const [startIndex, endIndex] of GRAPH_EDGES) {
    const start = GRAPH_NODES[startIndex].position;
    const end = GRAPH_NODES[endIndex].position;

    positions.push(
      start[0],
      start[1],
      start[2],
      end[0],
      end[1],
      end[2],
    );
  }

  const geometry = new BufferGeometry();

  geometry.setAttribute(
    "position",
    new BufferAttribute(new Float32Array(positions), 3),
  );

  return geometry;
}

function useMotionPreference() {
  const [reducedMotion, setReducedMotion] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);

  useEffect(() => {
    const media = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    );

    const updateMotion = () => {
      setReducedMotion(media.matches);
    };

    const updateVisibility = () => {
      setPageVisible(!document.hidden);
    };

    updateMotion();
    updateVisibility();

    media.addEventListener("change", updateMotion);
    document.addEventListener("visibilitychange", updateVisibility);

    return () => {
      media.removeEventListener("change", updateMotion);
      document.removeEventListener(
        "visibilitychange",
        updateVisibility,
      );
    };
  }, []);

  return {
    reducedMotion,
    pageVisible,
    animate: !reducedMotion && pageVisible,
  };
}

function advanceDotField(
  material: ShaderMaterial,
  points: Points | null,
  state: RootState,
  delta: number,
) {
  material.uniforms.uTime.value += Math.min(delta, 0.05);
  material.uniforms.uPixelRatio.value = Math.min(state.gl.getPixelRatio(), 1.5);

  if (points) {
    points.rotation.z = Math.sin(state.clock.elapsedTime * 0.08) * 0.012;
  }
}

function DotField({ animate }: { animate: boolean }) {
  const pointsRef = useRef<Points>(null);

  const geometry = useMemo(() => createDotGeometry(), []);

  const material = useMemo(
    () =>
      new ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uPixelRatio: { value: 1 },
        },
        vertexShader: DOT_VERTEX_SHADER,
        fragmentShader: DOT_FRAGMENT_SHADER,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    [],
  );

  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  useFrame((state, delta) => {
    if (!animate) return;
    advanceDotField(material, pointsRef.current, state, delta);
  });

  return (
    <points
      ref={pointsRef}
      geometry={geometry}
      material={material}
      frustumCulled={false}
    />
  );
}

function EvidenceGraph({ animate }: { animate: boolean }) {
  const groupRef = useRef<Group>(null);
  const focusNodeRef = useRef<Group>(null);

  const edgeGeometry = useMemo(
    () => createEdgeGeometry(),
    [],
  );

  const nodeGeometry = useMemo(
    () => GRAPH_NODES.map((node) => ({
      ...node,
      vector: new Vector3(...node.position),
      colorObject: new Color(node.color),
    })),
    [],
  );

  useEffect(() => {
    return () => {
      edgeGeometry.dispose();
    };
  }, [edgeGeometry]);

  useFrame((state, delta) => {
    if (!animate) return;

    const time = state.clock.elapsedTime;
    const group = groupRef.current;

    if (group) {
      group.rotation.y = MathUtils.damp(
        group.rotation.y,
        Math.sin(time * 0.16) * 0.075,
        2,
        delta,
      );

      group.rotation.x = MathUtils.damp(
        group.rotation.x,
        Math.cos(time * 0.13) * 0.025,
        2,
        delta,
      );

      group.position.y = Math.sin(time * 0.4) * 0.035;
    }

    if (focusNodeRef.current) {
      const pulse = (Math.sin(time * 1.15) + 1) * 0.5;

      focusNodeRef.current.scale.setScalar(
        1 + pulse * 0.12,
      );
    }
  });

  return (
    <group ref={groupRef}>
      <lineSegments geometry={edgeGeometry}>
        <lineBasicMaterial
          color={COLORS.blue}
          transparent
          opacity={0.3}
          depthWrite={false}
        />
      </lineSegments>

      {nodeGeometry.map((node) => {
        const isFocus = node.id === 5;

        return (
          <group
            key={node.id}
            position={node.vector}
            ref={isFocus ? focusNodeRef : undefined}
          >
            {isFocus && (
              <mesh>
                <sphereGeometry args={[0.3, 16, 16]} />
                <meshBasicMaterial
                  color={COLORS.blueLight}
                  transparent
                  opacity={0.1}
                  depthWrite={false}
                />
              </mesh>
            )}

            <mesh>
              <sphereGeometry
                args={[
                  node.radius,
                  12,
                  12,
                ]}
              />
              <meshStandardMaterial
                color={node.colorObject}
                roughness={0.45}
                metalness={0.05}
                emissive={node.colorObject}
                emissiveIntensity={0.12}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function SceneContent({ animate }: { animate: boolean }) {
  const pointerTarget = useRef({ x: 0, y: 0 });
  const pointerCurrent = useRef({ x: 0, y: 0 });
  const rootRef = useRef<Group>(null);

  const handlePointerMove = (event: ThreeEvent<PointerEvent>) => {
    pointerTarget.current.x = event.pointer.x;
    pointerTarget.current.y = event.pointer.y;
  };

  useFrame((_, delta) => {
    if (!animate) return;

    const root = rootRef.current;

    if (!root) return;

    pointerCurrent.current.x = MathUtils.damp(
      pointerCurrent.current.x,
      pointerTarget.current.x,
      1.6,
      delta,
    );

    pointerCurrent.current.y = MathUtils.damp(
      pointerCurrent.current.y,
      pointerTarget.current.y,
      1.6,
      delta,
    );

    root.rotation.y = pointerCurrent.current.x * 0.035;
    root.rotation.x = -pointerCurrent.current.y * 0.018;
  });

  return (
    <group
      ref={rootRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={() => {
        pointerTarget.current.x = 0;
        pointerTarget.current.y = 0;
      }}
    >
      <DotField animate={animate} />
      <EvidenceGraph animate={animate} />
    </group>
  );
}

export function HeroScene() {
  const { animate } = useMotionPreference();

  return (
    <div
      className="relative h-full w-full"
      aria-hidden="true"
    >
      <Canvas
        camera={{
          position: [0, 0.2, 8.5],
          fov: 38,
        }}
        dpr={[1, 1.5]}
        frameloop={animate ? "always" : "demand"}
        gl={{
          alpha: true,
          antialias: false,
          powerPreference: "low-power",
        }}
        fallback={
          <div className="h-full w-full rounded-3xl bg-gradient-to-br from-blue-50 to-white" />
        }
      >
        <Suspense fallback={null}>
          <ambientLight intensity={1.5} />
          <pointLight
            position={[2, 3, 5]}
            intensity={1.2}
            color={COLORS.blueLight}
          />

          <SceneContent animate={animate} />
        </Suspense>
      </Canvas>
    </div>
  );
}
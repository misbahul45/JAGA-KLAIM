"use client";

import { useFrame } from "@react-three/fiber";
import { useLayoutEffect, useMemo, useRef } from "react";
import {
  Color,
  InstancedMesh,
  MathUtils,
  Object3D,
  type Group,
  type Mesh,
  type ShaderMaterial,
} from "three";

import { DotPoster } from "@/components/shared/dot-poster";
import { SCENE_COLORS } from "@/components/three/palette";
import { SceneCanvas } from "@/components/three/scene-canvas";
import { usePointerRef } from "@/components/three/use-pointer-ref";
import { mulberry32 } from "@/lib/prng";

const COLS = 38;
const ROWS = 36;
const HALF_X = 3.7;
const HALF_Y = 4.2;

const DOT_VERTEX = `
  uniform float uTime;
  uniform vec2 uPointer;
  uniform float uPixelRatio;
  uniform vec2 uHalf;
  attribute float aSeed;
  attribute vec3 aColor;
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    float w1 = sin(p.x * 0.55 + uTime * 0.7 + aSeed * 0.6);
    float w2 = cos(p.y * 0.75 - uTime * 0.55);
    float wave = w1 * 0.55 + w2 * 0.45;
    p.z += wave * 0.55;
    float push = smoothstep(2.6, 0.0, distance(p.xy, uPointer));
    p.z += push * 1.1;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float edge = (1.0 - smoothstep(0.55, 1.0, abs(position.x) / uHalf.x)) *
      (1.0 - smoothstep(0.55, 1.0, abs(position.y) / uHalf.y));
    float size = (2.4 + aSeed * 1.8 + push * 3.2 + (wave * 0.5 + 0.5) * 1.2) * edge;
    gl_PointSize = size * uPixelRatio * (9.0 / -mv.z);
    vColor = aColor;
    vAlpha = 0.3 + 0.6 * (wave * 0.5 + 0.5) + push * 0.3;
  }
`;

const DOT_FRAGMENT = `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    float r = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.34, r) * vAlpha;
    if (a < 0.01) discard;
    gl_FragColor = vec4(vColor, a);
    #include <colorspace_fragment>
  }
`;

const EDGE_VERTEX = `
  attribute vec3 aColor;
  attribute float aT;
  attribute float aPhase;
  attribute float aStrength;
  varying vec3 vColor;
  varying float vT;
  varying float vPhase;
  varying float vStrength;

  void main() {
    vColor = aColor;
    vT = aT;
    vPhase = aPhase;
    vStrength = aStrength;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const EDGE_FRAGMENT = `
  uniform float uTime;
  varying vec3 vColor;
  varying float vT;
  varying float vPhase;
  varying float vStrength;

  void main() {
    float head = fract(uTime * 0.22 + vPhase);
    float pulse = smoothstep(0.22, 0.0, abs(vT - head));
    float a = (0.24 + pulse * 0.76) * vStrength;
    gl_FragColor = vec4(vColor, a);
    #include <colorspace_fragment>
  }
`;

function buildDotField() {
  const rand = mulberry32(7);
  const count = COLS * ROWS;
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  const colors = new Float32Array(count * 3);
  const palette = [
    { color: new Color(SCENE_COLORS.brand), weight: 0.6 },
    { color: new Color(SCENE_COLORS.magenta), weight: 0.14 },
    { color: new Color(SCENE_COLORS.orange), weight: 0.08 },
    { color: new Color(SCENE_COLORS.slate), weight: 0.18 },
  ];
  let i = 0;
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const u = c / (COLS - 1);
      const v = r / (ROWS - 1);
      positions[i * 3] = (u - 0.5) * HALF_X * 2 + (rand() - 0.5) * 0.08;
      positions[i * 3 + 1] = (v - 0.5) * HALF_Y * 2 + (rand() - 0.5) * 0.08;
      positions[i * 3 + 2] = 0;
      seeds[i] = rand();
      let pick = rand();
      let chosen = palette[0].color;
      for (const entry of palette) {
        if (pick < entry.weight) {
          chosen = entry.color;
          break;
        }
        pick -= entry.weight;
      }
      colors[i * 3] = chosen.r;
      colors[i * 3 + 1] = chosen.g;
      colors[i * 3 + 2] = chosen.b;
      i++;
    }
  }
  return { positions, seeds, colors };
}

type Kind = "expected" | "observed" | "delta" | "source";
type GraphNode = { p: [number, number, number]; kind: Kind; size: number };

function buildGraph() {
  const rand = mulberry32(21);
  const nodes: GraphNode[] = [];
  const expected: number[] = [];
  const observed: number[] = [];
  const sources: number[] = [];

  for (let i = 0; i < 6; i++) {
    const y = (i - 2.5) * 0.85;
    expected.push(nodes.length);
    nodes.push({
      p: [-2.15 + Math.sin(i * 1.3) * 0.2, y, (rand() - 0.5) * 1],
      kind: "expected",
      size: 0.115,
    });
  }
  for (let i = 0; i < 5; i++) {
    const y = (i - 2.5) * 0.85 + (rand() - 0.5) * 0.12;
    observed.push(nodes.length);
    nodes.push({
      p: [1.25 + Math.cos(i * 1.1) * 0.2, y, (rand() - 0.5) * 1],
      kind: "observed",
      size: 0.115,
    });
  }
  const deltaIndex = nodes.length;
  nodes.push({ p: [-0.45, 2.5 * 0.85, 0.25], kind: "delta", size: 0.15 });
  for (let i = 0; i < 9; i++) {
    sources.push(nodes.length);
    nodes.push({
      p: [
        2.3 + rand() * 1.1,
        (rand() - 0.5) * 4.6,
        (rand() - 0.5) * 2,
      ],
      kind: "source",
      size: 0.055,
    });
  }

  const edges: { a: number; b: number; color: Color; s: number }[] = [];
  const brand = new Color(SCENE_COLORS.brand);
  const orange = new Color(SCENE_COLORS.orange);
  const slate = new Color(SCENE_COLORS.slate);
  for (let i = 0; i < 5; i++) {
    edges.push({ a: expected[i], b: observed[i], color: brand, s: 1 });
  }
  edges.push({ a: expected[5], b: deltaIndex, color: orange, s: 1 });
  observed.forEach((o, i) => {
    edges.push({ a: o, b: sources[i], color: slate, s: 0.55 });
    edges.push({
      a: o,
      b: sources[(i * 2 + 3) % sources.length],
      color: slate,
      s: 0.4,
    });
  });

  const positions = new Float32Array(edges.length * 6);
  const colors = new Float32Array(edges.length * 6);
  const ts = new Float32Array(edges.length * 2);
  const phases = new Float32Array(edges.length * 2);
  const strengths = new Float32Array(edges.length * 2);
  edges.forEach((edge, i) => {
    const pa = nodes[edge.a].p;
    const pb = nodes[edge.b].p;
    positions.set(pa, i * 6);
    positions.set(pb, i * 6 + 3);
    colors.set([edge.color.r, edge.color.g, edge.color.b], i * 6);
    colors.set([edge.color.r, edge.color.g, edge.color.b], i * 6 + 3);
    ts[i * 2] = 0;
    ts[i * 2 + 1] = 1;
    const phase = rand();
    phases[i * 2] = phase;
    phases[i * 2 + 1] = phase;
    strengths[i * 2] = edge.s;
    strengths[i * 2 + 1] = edge.s;
  });

  return { nodes, deltaIndex, positions, colors, ts, phases, strengths };
}

const KIND_COLOR: Record<Kind, string> = {
  expected: SCENE_COLORS.brand,
  observed: SCENE_COLORS.mint,
  delta: SCENE_COLORS.orange,
  source: SCENE_COLORS.slate,
};

function DotField() {
  const material = useRef<ShaderMaterial>(null);
  const pointer = usePointerRef();
  const smooth = useRef({ x: 0, y: 0 });
  const data = useMemo(() => buildDotField(), []);
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPointer: { value: { x: 0, y: 0 } },
      uPixelRatio: { value: 1 },
      uHalf: { value: { x: HALF_X, y: HALF_Y } },
    }),
    [],
  );

  useFrame((state, delta) => {
    const mat = material.current;
    if (!mat) return;
    smooth.current.x = MathUtils.damp(smooth.current.x, pointer.current.x, 3, delta);
    smooth.current.y = MathUtils.damp(smooth.current.y, pointer.current.y, 3, delta);
    mat.uniforms.uTime.value = state.clock.elapsedTime;
    mat.uniforms.uPixelRatio.value = state.viewport.dpr;
    mat.uniforms.uPointer.value.x = smooth.current.x * 3.5;
    mat.uniforms.uPointer.value.y = smooth.current.y * 4;
  });

  return (
    <group rotation={[-1.05, 0, 0]} position={[0, -1.5, -0.6]}>
      <points frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[data.positions, 3]} />
          <bufferAttribute attach="attributes-aSeed" args={[data.seeds, 1]} />
          <bufferAttribute attach="attributes-aColor" args={[data.colors, 3]} />
        </bufferGeometry>
        <shaderMaterial
          ref={material}
          uniforms={uniforms}
          vertexShader={DOT_VERTEX}
          fragmentShader={DOT_FRAGMENT}
          transparent
          depthWrite={false}
        />
      </points>
    </group>
  );
}

function EvidenceGraph() {
  const group = useRef<Group>(null);
  const nodeMesh = useRef<InstancedMesh>(null);
  const haloMesh = useRef<InstancedMesh>(null);
  const deltaPulse = useRef<Mesh>(null);
  const edgeMaterial = useRef<ShaderMaterial>(null);
  const pointer = usePointerRef();
  const graph = useMemo(() => buildGraph(), []);
  const edgeUniforms = useMemo(() => ({ uTime: { value: 0 } }), []);

  useLayoutEffect(() => {
    const nodes = nodeMesh.current;
    const halos = haloMesh.current;
    if (!nodes || !halos) return;
    const dummy = new Object3D();
    const color = new Color();
    graph.nodes.forEach((node, i) => {
      color.set(KIND_COLOR[node.kind]);
      dummy.position.set(...node.p);
      dummy.scale.setScalar(node.size);
      dummy.updateMatrix();
      nodes.setMatrixAt(i, dummy.matrix);
      nodes.setColorAt(i, color);
      dummy.scale.setScalar(node.size * (node.kind === "source" ? 2 : 2.3));
      dummy.updateMatrix();
      halos.setMatrixAt(i, dummy.matrix);
      halos.setColorAt(i, color);
    });
    nodes.instanceMatrix.needsUpdate = true;
    halos.instanceMatrix.needsUpdate = true;
    if (nodes.instanceColor) nodes.instanceColor.needsUpdate = true;
    if (halos.instanceColor) halos.instanceColor.needsUpdate = true;
  }, [graph]);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    const g = group.current;
    if (g) {
      g.rotation.y = MathUtils.damp(
        g.rotation.y,
        Math.sin(t * 0.22) * 0.32 + pointer.current.x * 0.28,
        2.5,
        delta,
      );
      g.rotation.x = MathUtils.damp(
        g.rotation.x,
        -pointer.current.y * 0.14,
        2.5,
        delta,
      );
      g.position.y = Math.sin(t * 0.6) * 0.08 + 0.3;
      g.scale.setScalar(MathUtils.clamp(state.viewport.width / 7.4, 0.5, 1));
    }
    if (edgeMaterial.current) edgeMaterial.current.uniforms.uTime.value = t;
    if (deltaPulse.current) {
      deltaPulse.current.scale.setScalar(
        0.3 + (Math.sin(t * 2.2) * 0.5 + 0.5) * 0.3,
      );
    }
  });

  const deltaPosition = graph.nodes[graph.deltaIndex].p;
  const count = graph.nodes.length;

  return (
    <group ref={group} position={[0.15, 0.3, 0]}>
      <lineSegments frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[graph.positions, 3]} />
          <bufferAttribute attach="attributes-aColor" args={[graph.colors, 3]} />
          <bufferAttribute attach="attributes-aT" args={[graph.ts, 1]} />
          <bufferAttribute attach="attributes-aPhase" args={[graph.phases, 1]} />
          <bufferAttribute attach="attributes-aStrength" args={[graph.strengths, 1]} />
        </bufferGeometry>
        <shaderMaterial
          ref={edgeMaterial}
          uniforms={edgeUniforms}
          vertexShader={EDGE_VERTEX}
          fragmentShader={EDGE_FRAGMENT}
          transparent
          depthWrite={false}
        />
      </lineSegments>
      <instancedMesh ref={haloMesh} args={[undefined, undefined, count]} frustumCulled={false}>
        <sphereGeometry args={[1, 18, 12]} />
        <meshBasicMaterial transparent opacity={0.16} depthWrite={false} />
      </instancedMesh>
      <instancedMesh ref={nodeMesh} args={[undefined, undefined, count]} frustumCulled={false}>
        <sphereGeometry args={[1, 20, 14]} />
        <meshBasicMaterial />
      </instancedMesh>
      <mesh ref={deltaPulse} position={deltaPosition}>
        <sphereGeometry args={[0.5, 20, 14]} />
        <meshBasicMaterial
          color={SCENE_COLORS.orange}
          transparent
          opacity={0.28}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

export default function HeroScene() {
  return (
    <SceneCanvas
      camera={{ position: [0, 0.4, 9], fov: 38 }}
      fallback={<DotPoster />}
    >
      <DotField />
      <EvidenceGraph />
    </SceneCanvas>
  );
}

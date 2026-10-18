"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type RefObject } from "react";
import {
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  Line,
  LineBasicMaterial,
  MathUtils,
  Vector3,
  type Group,
  type Mesh,
  type MeshBasicMaterial,
} from "three";

import { DotPoster } from "@/components/shared/dot-poster";
import { SCENE_COLORS } from "@/components/three/palette";
import { SceneCanvas } from "@/components/three/scene-canvas";
import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";

const STAGE_COUNT = 7;
const AGENT_INDEX = 2;
const POLICY_INDEX = 4;

const IDLE = new Color("#27476b");
const DONE = new Color("#8b7bff");
const ACTIVE = new Color(SCENE_COLORS.white);

type Shared = {
  activeRef: RefObject<number>;
  rateRef: RefObject<number>;
};

function buildPath() {
  const curve = new CatmullRomCurve3([
    new Vector3(-7.2, -0.7, 0),
    new Vector3(-4.6, 0.8, 0.6),
    new Vector3(-2.2, -0.5, -0.4),
    new Vector3(0, 0.7, 0.4),
    new Vector3(2.2, -0.6, -0.2),
    new Vector3(4.6, 0.8, 0.5),
    new Vector3(7.2, -0.4, 0),
  ]);
  const nodes = Array.from({ length: STAGE_COUNT }, (_, i) =>
    curve.getPointAt(i / (STAGE_COUNT - 1)),
  );
  const points = curve.getPoints(160);
  return { curve, nodes, points };
}

function colorGap(a: Color, b: Color) {
  return Math.abs(a.r - b.r) + Math.abs(a.g - b.g) + Math.abs(a.b - b.b);
}

function StageNode({
  position,
  index,
  activeRef,
  rateRef,
}: Shared & { position: Vector3; index: number }) {
  const core = useRef<Mesh>(null);
  const coreMaterial = useRef<MeshBasicMaterial>(null);
  const halo = useRef<Mesh>(null);
  const haloMaterial = useRef<MeshBasicMaterial>(null);
  const ring = useRef<Mesh>(null);

  useFrame((state, delta) => {
    const mesh = core.current;
    const material = coreMaterial.current;
    const haloMesh = halo.current;
    const haloMat = haloMaterial.current;
    if (!mesh || !material || !haloMesh || !haloMat) return;

    const rate = rateRef.current;
    const active = activeRef.current;
    const isActive = index === active;
    const target = isActive ? ACTIVE : index < active ? DONE : IDLE;
    const pulse = isActive ? Math.sin(state.clock.elapsedTime * 3) * 0.06 : 0;
    const scale = (isActive ? 1.4 : index < active ? 1 : 0.8) + pulse;
    const haloScale = isActive ? 2.8 + pulse * 3 : 1.6;
    const haloOpacity = isActive ? 0.28 : index < active ? 0.1 : 0.03;

    material.color.lerp(target, 1 - Math.exp(-rate * delta));
    mesh.scale.setScalar(MathUtils.damp(mesh.scale.x, scale, rate, delta));
    haloMesh.scale.setScalar(MathUtils.damp(haloMesh.scale.x, haloScale, rate, delta));
    haloMat.opacity = MathUtils.damp(haloMat.opacity, haloOpacity, rate, delta);
    if (ring.current) ring.current.rotation.z += delta * 0.9;

    const settling =
      colorGap(material.color, target) > 0.003 ||
      Math.abs(mesh.scale.x - scale) > 0.002 ||
      Math.abs(haloMat.opacity - haloOpacity) > 0.002;
    if (settling) state.invalidate();
  });

  return (
    <group position={position}>
      <mesh ref={halo}>
        <sphereGeometry args={[0.3, 20, 14]} />
        <meshBasicMaterial
          ref={haloMaterial}
          color={index === POLICY_INDEX ? SCENE_COLORS.sun : SCENE_COLORS.brand}
          transparent
          opacity={0.05}
          depthWrite={false}
        />
      </mesh>
      <mesh ref={core}>
        {index === POLICY_INDEX ? (
          <boxGeometry args={[0.5, 0.5, 0.5]} />
        ) : (
          <sphereGeometry args={[0.3, 24, 16]} />
        )}
        <meshBasicMaterial ref={coreMaterial} color={IDLE} />
      </mesh>
      {index === AGENT_INDEX ? (
        <mesh ref={ring} rotation={[1.1, 0.3, 0]}>
          <torusGeometry args={[0.62, 0.018, 8, 56]} />
          <meshBasicMaterial color={SCENE_COLORS.magenta} transparent opacity={0.85} />
        </mesh>
      ) : null}
    </group>
  );
}

function PipelineRig({ activeIndex }: { activeIndex: number }) {
  const reducedMotion = usePrefersReducedMotion();
  const invalidate = useThree((state) => state.invalidate);
  const activeRef = useRef(activeIndex);
  const rateRef = useRef(8);
  const group = useRef<Group>(null);
  const packet = useRef<Mesh>(null);
  const packetT = useRef(0);
  const progress = useRef(0);
  const scratch = useMemo(() => new Vector3(), []);
  const path = useMemo(() => buildPath(), []);

  const lines = useMemo(() => {
    const base = new Line(
      new BufferGeometry().setFromPoints(path.points),
      new LineBasicMaterial({ color: SCENE_COLORS.slate, transparent: true, opacity: 0.35 }),
    );
    const done = new Line(
      new BufferGeometry().setFromPoints(path.points),
      new LineBasicMaterial({ color: "#8b7bff", transparent: true, opacity: 0.95 }),
    );
    done.geometry.setDrawRange(0, 2);
    return { base, done };
  }, [path]);

  useEffect(() => {
    return () => {
      lines.base.geometry.dispose();
      lines.base.material.dispose();
      lines.done.geometry.dispose();
      lines.done.material.dispose();
    };
  }, [lines]);

  useEffect(() => {
    activeRef.current = activeIndex;
    rateRef.current = reducedMotion ? 1000 : 8;
    invalidate();
  }, [activeIndex, reducedMotion, invalidate]);

  const boundary = useMemo(
    () => path.nodes[POLICY_INDEX - 1].clone().lerp(path.nodes[POLICY_INDEX], 0.5),
    [path],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (g) {
      g.scale.setScalar(MathUtils.clamp(state.viewport.width / 16.5, 0.36, 1));
    }
    const rate = rateRef.current;
    const targetT = activeRef.current / (STAGE_COUNT - 1);
    packetT.current = MathUtils.damp(packetT.current, targetT, rate * 0.45, delta);
    progress.current = MathUtils.damp(progress.current, targetT, rate * 0.45, delta);
    if (packet.current) {
      path.curve.getPointAt(MathUtils.clamp(packetT.current, 0, 1), scratch);
      packet.current.position.copy(scratch);
      packet.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 4) * 0.12);
    }
    lines.done.geometry.setDrawRange(
      0,
      Math.max(2, Math.round(progress.current * (path.points.length - 1)) + 1),
    );
    if (
      Math.abs(packetT.current - targetT) > 0.0008 ||
      Math.abs(progress.current - targetT) > 0.0008
    ) {
      state.invalidate();
    }
  });

  return (
    <group ref={group}>
      <primitive object={lines.base} />
      <primitive object={lines.done} />
      <group position={boundary}>
        <mesh>
          <planeGeometry args={[0.7, 3.6]} />
          <meshBasicMaterial
            color={SCENE_COLORS.sun}
            transparent
            opacity={0.07}
            depthWrite={false}
          />
        </mesh>
        <mesh>
          <planeGeometry args={[0.035, 3.6]} />
          <meshBasicMaterial color={SCENE_COLORS.sun} transparent opacity={0.8} />
        </mesh>
      </group>
      {path.nodes.map((position, index) => (
        <StageNode
          key={index}
          position={position}
          index={index}
          activeRef={activeRef}
          rateRef={rateRef}
        />
      ))}
      <mesh ref={packet}>
        <sphereGeometry args={[0.12, 16, 12]} />
        <meshBasicMaterial color={SCENE_COLORS.orange} />
      </mesh>
    </group>
  );
}

export default function PipelineScene({ activeIndex }: { activeIndex: number }) {
  return (
    <SceneCanvas
      camera={{ position: [0, 0, 11], fov: 35 }}
      fallback={<DotPoster tone="dark" />}
      dpr={[1, 1.75]}
    >
      <PipelineRig activeIndex={activeIndex} />
    </SceneCanvas>
  );
}

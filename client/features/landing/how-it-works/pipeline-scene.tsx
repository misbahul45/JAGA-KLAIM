"use client";

import { useFrame, useThree } from "@react-three/fiber";
import {
  useEffect,
  useMemo,
  useRef,
  type MutableRefObject,
} from "react";
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
  activeRef: MutableRefObject<number>;
  rateRef: MutableRefObject<number>;
  reducedMotion: boolean;
};

function buildPath() {
  const curve = new CatmullRomCurve3([
    new Vector3(-7.2, -0.7, 0),
    new Vector3(-4.8, 0.8, 0.5),
    new Vector3(-2.4, -0.5, -0.3),
    new Vector3(0, 0.7, 0.3),
    new Vector3(2.4, -0.6, -0.2),
    new Vector3(4.8, 0.8, 0.4),
    new Vector3(7.2, -0.4, 0),
  ]);

  const nodes = Array.from({ length: STAGE_COUNT }, (_, index) =>
    curve.getPointAt(index / (STAGE_COUNT - 1)),
  );

  const points = curve.getPoints(160);

  return { curve, nodes, points };
}

function colorGap(a: Color, b: Color) {
  return (
    Math.abs(a.r - b.r) +
    Math.abs(a.g - b.g) +
    Math.abs(a.b - b.b)
  );
}

function StageNode({
  position,
  index,
  activeRef,
  rateRef,
  reducedMotion,
}: Shared & {
  position: Vector3;
  index: number;
}) {
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

    const active = activeRef.current;
    const isActive = index === active;
    const isDone = index < active;

    const targetColor = isActive ? ACTIVE : isDone ? DONE : IDLE;
    const pulse =
      isActive && !reducedMotion
        ? Math.sin(state.clock.elapsedTime * 3) * 0.055
        : 0;

    const targetScale = (isActive ? 1.35 : isDone ? 1 : 0.8) + pulse;
    const targetHaloScale = isActive ? 2.6 + pulse * 3 : isDone ? 1.5 : 1.3;
    const targetHaloOpacity = isActive ? 0.25 : isDone ? 0.1 : 0.035;
    const rate = rateRef.current;

    if (reducedMotion) {
      material.color.copy(targetColor);
      mesh.scale.setScalar(targetScale);
      haloMesh.scale.setScalar(targetHaloScale);
      haloMat.opacity = targetHaloOpacity;
    } else {
      material.color.lerp(
        targetColor,
        1 - Math.exp(-rate * delta),
      );

      mesh.scale.setScalar(
        MathUtils.damp(mesh.scale.x, targetScale, rate, delta),
      );

      haloMesh.scale.setScalar(
        MathUtils.damp(haloMesh.scale.x, targetHaloScale, rate, delta),
      );

      haloMat.opacity = MathUtils.damp(
        haloMat.opacity,
        targetHaloOpacity,
        rate,
        delta,
      );
    }

    if (ring.current && !reducedMotion) {
      ring.current.rotation.z += delta * 0.65;
    }

    if (reducedMotion) return;

    const settling =
      colorGap(material.color, targetColor) > 0.003 ||
      Math.abs(mesh.scale.x - targetScale) > 0.002 ||
      Math.abs(haloMat.opacity - targetHaloOpacity) > 0.002;

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
          opacity={0.035}
          depthWrite={false}
        />
      </mesh>

      <mesh ref={core}>
        {index === POLICY_INDEX ? (
          <boxGeometry args={[0.48, 0.48, 0.48]} />
        ) : (
          <sphereGeometry args={[0.3, 24, 16]} />
        )}

        <meshBasicMaterial ref={coreMaterial} color={IDLE} />
      </mesh>

      {index === AGENT_INDEX && (
        <mesh ref={ring} rotation={[1.1, 0.3, 0]}>
          <torusGeometry args={[0.62, 0.018, 8, 56]} />

          <meshBasicMaterial
            color={SCENE_COLORS.magenta}
            transparent
            opacity={0.85}
          />
        </mesh>
      )}
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
      new LineBasicMaterial({
        color: SCENE_COLORS.slate,
        transparent: true,
        opacity: 0.4,
      }),
    );

    const done = new Line(
      new BufferGeometry().setFromPoints(path.points),
      new LineBasicMaterial({
        color: "#8b7bff",
        transparent: true,
        opacity: 0.95,
      }),
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
    activeRef.current = MathUtils.clamp(
      activeIndex,
      0,
      STAGE_COUNT - 1,
    );

    rateRef.current = reducedMotion ? 1000 : 8;

    if (reducedMotion) {
      const target = activeRef.current / (STAGE_COUNT - 1);
      packetT.current = target;
      progress.current = target;
    }

    invalidate();
  }, [activeIndex, reducedMotion, invalidate]);

  const boundary = useMemo(
    () =>
      path.nodes[POLICY_INDEX - 1]
        .clone()
        .lerp(path.nodes[POLICY_INDEX], 0.5),
    [path],
  );

  useFrame((state, delta) => {
    const currentGroup = group.current;

    if (currentGroup) {
      const targetScale = MathUtils.clamp(
        state.viewport.width / 16.5,
        0.36,
        1,
      );

      currentGroup.scale.setScalar(targetScale);
    }

    const targetT = activeRef.current / (STAGE_COUNT - 1);
    const rate = rateRef.current;

    if (reducedMotion) {
      packetT.current = targetT;
      progress.current = targetT;
    } else {
      packetT.current = MathUtils.damp(
        packetT.current,
        targetT,
        rate * 0.45,
        delta,
      );

      progress.current = MathUtils.damp(
        progress.current,
        targetT,
        rate * 0.45,
        delta,
      );
    }

    if (packet.current) {
      path.curve.getPointAt(
        MathUtils.clamp(packetT.current, 0, 1),
        scratch,
      );

      packet.current.position.copy(scratch);

      const pulse = reducedMotion
        ? 1
        : 1 + Math.sin(state.clock.elapsedTime * 4) * 0.1;

      packet.current.scale.setScalar(pulse);
    }

    lines.done.geometry.setDrawRange(
      0,
      Math.max(
        2,
        Math.round(progress.current * (path.points.length - 1)) + 1,
      ),
    );

    if (
      !reducedMotion &&
      (
        Math.abs(packetT.current - targetT) > 0.0008 ||
        Math.abs(progress.current - targetT) > 0.0008
      )
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

          <meshBasicMaterial
            color={SCENE_COLORS.sun}
            transparent
            opacity={0.8}
          />
        </mesh>
      </group>

      {path.nodes.map((position, index) => (
        <StageNode
          key={index}
          position={position}
          index={index}
          activeRef={activeRef}
          rateRef={rateRef}
          reducedMotion={reducedMotion}
        />
      ))}

      <mesh ref={packet}>
        <sphereGeometry args={[0.12, 16, 12]} />

        <meshBasicMaterial color={SCENE_COLORS.orange} />
      </mesh>
    </group>
  );
}

export default function PipelineScene({
  activeIndex,
}: {
  activeIndex: number;
}) {
  return (
    <SceneCanvas
      camera={{ position: [0, 0, 11], fov: 35 }}
      fallback={<DotPoster tone="dark" />}
      dpr={[1, 1.5]}
    >
      <PipelineRig activeIndex={activeIndex} />
    </SceneCanvas>
  );
}
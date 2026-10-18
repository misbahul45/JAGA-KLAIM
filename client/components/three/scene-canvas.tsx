"use client";

import { Canvas, type CanvasProps } from "@react-three/fiber";
import {
  Component,
  Suspense,
  useState,
  type ErrorInfo,
  type ReactNode,
} from "react";

import { useInView } from "@/hooks/use-in-view";
import { usePrefersReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

type SceneCanvasProps = {
  children: ReactNode;
  fallback?: ReactNode;
  className?: string;
  camera?: CanvasProps["camera"];
  dpr?: [number, number];
  rootMargin?: string;
};

type BoundaryProps = { fallback: ReactNode; children: ReactNode };
type BoundaryState = { failed: boolean };

class SceneBoundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { failed: false };

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Scene gagal dirender", error, info.componentStack);
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function detectWebGL() {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const gl = (canvas.getContext("webgl2") ??
      canvas.getContext("webgl")) as WebGLRenderingContext | null;
    if (!gl) return false;
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

export function SceneCanvas({
  children,
  fallback = null,
  className,
  camera,
  dpr = [1, 1.5],
  rootMargin = "160px",
}: SceneCanvasProps) {
  const [hostRef, inView] = useInView<HTMLDivElement>({ rootMargin });
  const reducedMotion = usePrefersReducedMotion();
  const [supported] = useState(detectWebGL);

  return (
    <div ref={hostRef} aria-hidden="true" className={cn("size-full", className)}>
      {supported ? (
        <SceneBoundary fallback={fallback}>
          <Canvas
            flat
            frameloop={inView && !reducedMotion ? "always" : "demand"}
            dpr={dpr}
            camera={camera}
            resize={{ scroll: false }}
            gl={{
              antialias: true,
              alpha: true,
              powerPreference: "high-performance",
            }}
          >
            <Suspense fallback={null}>{children}</Suspense>
          </Canvas>
        </SceneBoundary>
      ) : (
        fallback
      )}
    </div>
  );
}

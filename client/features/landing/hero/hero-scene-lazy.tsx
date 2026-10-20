"use client";

import dynamic from "next/dynamic";

import { DotPoster } from "@/components/shared/dot-poster";
import { useIdle } from "@/hooks/use-idle";

const HeroScene = dynamic(() => import("./hero-scene").then((module) => module.HeroScene), {
  ssr: false,
  loading: () => <DotPoster />,
});

export function HeroSceneLazy() {
  const idle = useIdle();
  return idle ? <HeroScene /> : <DotPoster />;
}

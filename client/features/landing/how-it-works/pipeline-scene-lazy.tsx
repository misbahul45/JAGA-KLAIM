"use client";

import dynamic from "next/dynamic";

import { DotPoster } from "@/components/shared/dot-poster";
import { useInView } from "@/hooks/use-in-view";

const PipelineScene = dynamic(() => import("./pipeline-scene"), {
  ssr: false,
  loading: () => <DotPoster tone="dark" />,
});

export function PipelineSceneLazy({
  activeIndex,
}: {
  activeIndex: number;
}) {
  const [hostRef, near] = useInView<HTMLDivElement>({
    rootMargin: "400px",
    once: true,
  });

  return (
    <div ref={hostRef} className="size-full">
      {near ? (
        <PipelineScene activeIndex={activeIndex} />
      ) : (
        <DotPoster tone="dark" />
      )}
    </div>
  );
}
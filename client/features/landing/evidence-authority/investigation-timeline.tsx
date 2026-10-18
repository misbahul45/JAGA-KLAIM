"use client";

import { useRef } from "react";

import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

import { TIMELINE_STEPS } from "./data";

export function InvestigationTimeline() {
  const listRef = useRef<HTMLOListElement>(null);
  const lineRef = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        gsap.fromTo(
          lineRef.current,
          { scaleY: 0 },
          {
            scaleY: 1,
            ease: "none",
            scrollTrigger: {
              trigger: listRef.current,
              start: "top 75%",
              end: "bottom 60%",
              scrub: true,
            },
          },
        );
        gsap.from("[data-step-dot]", {
          scale: 0,
          duration: 0.5,
          ease: "back.out(2)",
          stagger: 0.12,
          scrollTrigger: { trigger: listRef.current, start: "top 78%", once: true },
        });
      });
    },
    { scope: listRef },
  );

  return (
    <ol ref={listRef} className="relative flex flex-col gap-6">
      <span
        aria-hidden="true"
        className="absolute top-2 bottom-2 left-[0.6rem] w-px bg-line"
      />
      <span
        ref={lineRef}
        aria-hidden="true"
        className="absolute top-2 bottom-2 left-[0.6rem] w-px origin-top bg-brand"
      />
      {TIMELINE_STEPS.map((step) => (
        <li key={step} className="relative flex items-start gap-4">
          <span
            data-step-dot
            aria-hidden="true"
            className="relative z-10 mt-1 size-[1.3rem] shrink-0 rounded-full border-4 border-background bg-brand"
          />
          <p className="text-[0.95rem] leading-relaxed text-ink">{step}</p>
        </li>
      ))}
    </ol>
  );
}

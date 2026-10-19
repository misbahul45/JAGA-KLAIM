"use client";

import { useRef } from "react";

import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

import { TIMELINE_STEPS } from "./data";

export function InvestigationTimeline() {
  const listRef = useRef<HTMLOListElement>(null);
  const lineRef = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      const list = listRef.current;
      const line = lineRef.current;

      if (!list || !line) return;

      const mm = gsap.matchMedia();

      mm.add(MOTION_OK, () => {
        gsap.fromTo(
          line,
          {
            scaleY: 0,
          },
          {
            scaleY: 1,
            ease: "none",
            scrollTrigger: {
              trigger: list,
              start: "top 78%",
              end: "bottom 62%",
              scrub: 0.6,
            },
          },
        );

        const dots = gsap.utils.toArray<HTMLElement>(
          "[data-step-dot]",
          list,
        );

        gsap.fromTo(
          dots,
          {
            scale: 0.65,
            opacity: 0.45,
          },
          {
            scale: 1,
            opacity: 1,
            duration: 0.45,
            ease: "power2.out",
            stagger: 0.1,
            scrollTrigger: {
              trigger: list,
              start: "top 78%",
              once: true,
            },
          },
        );
      });

      return () => mm.revert();
    },
    { scope: listRef },
  );

  return (
    <ol
      ref={listRef}
      aria-label="Tahapan investigasi bukti"
      className="relative flex flex-col gap-6"
    >
      <span
        aria-hidden="true"
        className="absolute top-2 bottom-2 left-[0.6rem] w-px bg-line"
      />

      <span
        ref={lineRef}
        aria-hidden="true"
        className="absolute top-2 bottom-2 left-[0.6rem] w-px origin-top bg-brand"
      />

      {TIMELINE_STEPS.map((step, index) => (
        <li
          key={step}
          className="relative flex items-start gap-4"
        >
          <span
            data-step-dot
            aria-hidden="true"
            className="relative z-10 mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border-[3px] border-background bg-brand ring-1 ring-brand/20"
          >
            <span className="size-1.5 rounded-full bg-white" />
          </span>

          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-muted-foreground">
              LANGKAH {String(index + 1).padStart(2, "0")}
            </p>

            <p className="mt-1 text-sm leading-relaxed text-ink">
              {step}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
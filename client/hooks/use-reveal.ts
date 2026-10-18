import type { RefObject } from "react";

import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

export function useReveal(scope: RefObject<HTMLElement | null>) {
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
          gsap.from(element, {
            y: 40,
            autoAlpha: 0,
            duration: 0.9,
            ease: "power3.out",
            clearProps: "opacity,visibility,transform",
            scrollTrigger: { trigger: element, start: "top 88%", once: true },
          });
        });

        gsap.utils
          .toArray<HTMLElement>("[data-reveal-group]")
          .forEach((group) => {
            const items = group.querySelectorAll<HTMLElement>(
              "[data-reveal-item]",
            );
            if (!items.length) return;
            gsap.from(items, {
              y: 32,
              autoAlpha: 0,
              duration: 0.8,
              ease: "power3.out",
              stagger: 0.09,
              clearProps: "opacity,visibility,transform",
              scrollTrigger: { trigger: group, start: "top 85%", once: true },
            });
          });
      });
    },
    { scope },
  );
}

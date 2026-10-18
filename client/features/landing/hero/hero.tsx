"use client";

import { ArrowRightIcon } from "lucide-react";
import { useRef } from "react";

import { ButtonLink } from "@/components/shared/button-link";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

import { HeroSceneLazy } from "./hero-scene-lazy";

export function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const visualRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        gsap.to(visualRef.current, {
          yPercent: 8,
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top top",
            end: "bottom top",
            scrub: true,
          },
        });
      });
    },
    { scope: sectionRef },
  );

  return (
    <section
      id="beranda"
      ref={sectionRef}
      aria-labelledby="hero-title"
      className="relative isolate overflow-hidden pt-28 pb-16 sm:pt-36 lg:pb-24"
    >
      <div aria-hidden="true" className="bg-dots absolute inset-0 -z-10 opacity-50" />

      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-[1.02fr_1fr]">
        <div className="flex flex-col items-start gap-6">
          <h1
            id="hero-title"
            className="animate-rise text-[clamp(2.6rem,10.5vw,4.75rem)] leading-none font-semibold tracking-[-0.05em] whitespace-nowrap text-brand"
            style={{ animationDelay: "80ms" }}
          >
            JAGA-KLAIM
          </h1>
          <h2
            className="animate-rise text-3xl leading-[1.1] font-semibold tracking-[-0.035em] text-balance text-ink sm:text-4xl lg:text-[2.75rem]"
            style={{ animationDelay: "160ms" }}
          >
            memeriksa klaim dengan bukti, sebelum diajukan.
          </h2>
          <p
            className="animate-rise max-w-xl text-lg leading-relaxed text-pretty text-muted-foreground"
            style={{ animationDelay: "240ms" }}
          >
            AI-powered pre-claim verification copilot untuk koder dan verifikator
            internal fasilitas kesehatan. Membantu memeriksa konsistensi coding
            dengan bukti klinis dan operasional sebelum klaim diajukan, tanpa
            mengambil alih keputusan manusia.
          </p>
          <div
            className="animate-rise flex flex-wrap items-center gap-3 pt-2"
            style={{ animationDelay: "320ms" }}
          >
            <ButtonLink href="#cara-kerja" variant="brand" size="xl">
              Pelajari Cara Kerja
              <ArrowRightIcon data-icon="inline-end" />
            </ButtonLink>
            <ButtonLink href="#bukti" variant="outline" size="xl">
              Jelajahi Arsitektur
            </ButtonLink>
          </div>
        </div>

        <div
          ref={visualRef}
          className="animate-rise relative mx-auto aspect-[5/4] w-full max-w-xl lg:aspect-square lg:max-w-none"
          style={{ animationDelay: "200ms" }}
        >
          <HeroSceneLazy />
        </div>
      </div>
    </section>
  );
}

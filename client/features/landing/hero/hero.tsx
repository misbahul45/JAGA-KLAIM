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
      const media = gsap.matchMedia();

      media.add(MOTION_OK, () => {
        const section = sectionRef.current;
        const visual = visualRef.current;

        if (!section || !visual) return;

        gsap.to(visual, {
          yPercent: 3,
          ease: "none",
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: "bottom top",
            scrub: 0.8,
          },
        });
      });

      return () => media.revert();
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
      <div
        aria-hidden="true"
        className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-35"
      />

      <div className="mx-auto grid w-full max-w-6xl items-center gap-10 px-5 sm:px-8 lg:grid-cols-[1fr_0.95fr] lg:gap-12">
        <div className="flex min-w-0 flex-col items-start gap-6">
          <h1
            id="hero-title"
            className="animate-rise max-w-full text-[clamp(2.35rem,7vw,4.5rem)] leading-[1.02] font-semibold tracking-[-0.055em] text-brand"
            style={{ animationDelay: "80ms" }}
          >
            JAGA-KLAIM
          </h1>

          <h2
            className="animate-rise max-w-xl text-[clamp(1.9rem,4.2vw,3.25rem)] leading-[1.12] font-semibold tracking-[-0.04em] text-balance text-ink"
            style={{ animationDelay: "160ms" }}
          >
            Periksa klaim lebih awal, sebelum diajukan.
          </h2>

          <p
            className="animate-rise max-w-xl text-base leading-8 text-pretty text-muted-foreground sm:text-lg"
            style={{ animationDelay: "240ms" }}
          >
            JAGA-KLAIM membantu koder dan verifikator fasilitas kesehatan
            memeriksa kesesuaian kode dengan bukti pendukung. Temuan yang
            dihasilkan dapat ditinjau manusia sebelum menentukan tindak lanjut.
          </p>

          <div
            className="animate-rise flex w-full flex-col items-stretch gap-3 pt-1 sm:w-auto sm:flex-row sm:items-center"
            style={{ animationDelay: "320ms" }}
          >
            <ButtonLink
              href="#cara-kerja"
              variant="brand"
              size="xl"
            >
              Pelajari Cara Kerja
              <ArrowRightIcon
                aria-hidden="true"
                data-icon="inline-end"
              />
            </ButtonLink>

            <ButtonLink
              href="#bukti"
              variant="outline"
              size="xl"
            >
              Lihat Contoh Pemeriksaan
            </ButtonLink>
          </div>
        </div>

        <div
          ref={visualRef}
          className="relative mx-auto aspect-[5/4] w-full max-w-lg lg:aspect-square lg:max-w-none"
        >
          <HeroSceneLazy />
        </div>
      </div>
    </section>
  );
}
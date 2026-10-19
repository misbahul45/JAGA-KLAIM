"use client";

import { ShieldCheckIcon } from "lucide-react";
import { useRef, useState } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/use-reveal";

import { PRINCIPLES, STAGES } from "./data";
import { PipelineCarousel } from "./pipeline-carousel";
import { PipelineSceneLazy } from "./pipeline-scene-lazy";

export function HowItWorks() {
  const sectionRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);

  useReveal(sectionRef);

  return (
    <SectionShell id="cara-kerja" tone="dark" ref={sectionRef}>
      <div
        aria-hidden="true"
        className="bg-dots-light pointer-events-none absolute inset-0 -z-10 opacity-40"
      />

      <SectionHeading
        id="cara-kerja"
        tone="dark"
        title="Dari klaim masuk hingga keputusan yang terarah."
        lead="JAGA-KLAIM menelusuri bukti, mengidentifikasi perbedaan, dan membantu verifikator meninjau temuan sebelum mengambil keputusan."
      />

      <div className="mt-10 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-medium text-white/70">
          Alur pemeriksaan klaim
        </p>

        <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs text-white/65">
          {String(active + 1).padStart(2, "0")} /{" "}
          {String(STAGES.length).padStart(2, "0")} tahap
        </span>
      </div>

      <div
        data-reveal
        className="relative mt-4 h-[220px] overflow-hidden rounded-3xl bg-[#081426] ring-1 ring-white/10 sm:h-[280px] lg:h-[330px]"
      >
        <PipelineSceneLazy activeIndex={active} />

        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#081426]/70 to-transparent"
        />
      </div>

      <div data-reveal className="mt-7">
        <PipelineCarousel onActiveChange={setActive} />
      </div>

      <div className="mt-16">
        <div data-reveal className="max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-mint">
            Prinsip utama
          </p>

          <h3 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            Transparan dalam proses. Terukur dalam keputusan.
          </h3>

          <p className="mt-3 text-sm leading-relaxed text-white/60 sm:text-base">
            Setiap temuan perlu memiliki dasar yang jelas, aturan yang
            konsisten, dan ruang penilaian bagi manusia.
          </p>
        </div>

        <ul
          data-reveal-group
          className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {PRINCIPLES.map((principle, index) => (
            <li
              key={principle.title}
              data-reveal-item
              className="flex"
            >
              <Card className="w-full gap-0 rounded-2xl bg-white/[0.04] p-5 text-base text-white ring-1 ring-white/10 transition-colors duration-300 hover:bg-white/[0.07]">
                <div className="flex items-center justify-between">
                  <ShieldCheckIcon
                    className="size-5 text-mint"
                    aria-hidden="true"
                  />

                  <span
                    aria-hidden="true"
                    className="font-mono text-sm text-white/30"
                  >
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>

                <h4 className="mt-5 font-semibold tracking-tight text-white">
                  {principle.title}
                </h4>

                <p className="mt-2 text-sm leading-relaxed text-white/60">
                  {principle.text}
                </p>
              </Card>
            </li>
          ))}
        </ul>
      </div>
    </SectionShell>
  );
}
"use client";

import { ShieldCheckIcon } from "lucide-react";
import { useRef, useState } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/use-reveal";

import { PRINCIPLES } from "./data";
import { PipelineCarousel } from "./pipeline-carousel";
import { PipelineSceneLazy } from "./pipeline-scene-lazy";

export function HowItWorks() {
  const sectionRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);

  useReveal(sectionRef);

  return (
    <SectionShell id="cara-kerja" tone="dark" ref={sectionRef}>
      <div aria-hidden="true" className="bg-dots-light absolute inset-0 -z-10 opacity-60" />

      <SectionHeading
        id="cara-kerja"
        tone="dark"
        title="Tujuh tahap dari klaim masuk hingga temuan yang bisa diperiksa."
        lead="Alur ini menjadi penjelasan utama JAGA-KLAIM: dari hasil coding dan grouping INA-CBG, melalui penelusuran bukti oleh AI agent, hingga keputusan yang tetap berada di tangan manusia."
      />

      <div
        data-reveal
        className="relative mt-12 h-[250px] overflow-hidden rounded-[2rem] bg-white/[0.03] ring-1 ring-white/10 sm:h-[320px]"
      >
        <PipelineSceneLazy activeIndex={active} />
      </div>

      <div data-reveal className="mt-8">
        <PipelineCarousel onActiveChange={setActive} />
      </div>

      <ul data-reveal-group className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PRINCIPLES.map((principle) => (
          <li key={principle.title} data-reveal-item className="flex">
            <Card className="w-full gap-0 rounded-3xl bg-white/[0.05] p-6 text-base text-white ring-1 ring-white/10">
              <ShieldCheckIcon className="size-5 text-mint" aria-hidden="true" />
              <p className="mt-4 font-semibold tracking-[-0.02em] text-white">
                {principle.title}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-white/65">{principle.text}</p>
            </Card>
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}

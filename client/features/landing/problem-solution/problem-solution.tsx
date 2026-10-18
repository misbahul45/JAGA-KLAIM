"use client";

import { InfoIcon } from "lucide-react";
import { useRef } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/use-reveal";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";

import { PROBLEMS, SOLUTION_STEPS } from "./data";

export function ProblemSolution() {
  const sectionRef = useRef<HTMLElement>(null);
  const listRef = useRef<HTMLOListElement>(null);
  const lineRef = useRef<HTMLSpanElement>(null);

  useReveal(sectionRef);

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
      });
    },
    { scope: sectionRef },
  );

  return (
    <SectionShell id="masalah" ref={sectionRef}>
      <SectionHeading
        id="masalah"
        title="Ketidaksesuaian sebaiknya ditemukan sebelum klaim diajukan."
        lead="Ketika ketidaksesuaian baru ditemukan pada tahap berikutnya, koreksi dan klarifikasi menjadi pekerjaan tambahan. JAGA-KLAIM memindahkan pemeriksaan ke titik yang lebih awal: setelah coding dan grouping INA-CBG, sebelum klaim diajukan."
      />

      <div data-reveal-group className="mt-14 grid gap-6 lg:grid-cols-2">
        <Card
          data-reveal-item
          className="gap-0 rounded-3xl bg-white p-7 text-base ring-1 ring-line sm:p-9"
        >
          <p className="text-2xl font-semibold tracking-[-0.03em]">
            Apa yang sulit hari ini
          </p>
          <ul className="mt-7 flex flex-col gap-6">
            {PROBLEMS.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-ruby/10 text-ruby">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="font-semibold text-ink">{title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                    {text}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card
          data-reveal-item
          className="gap-0 rounded-3xl bg-bento-lavender p-7 text-base ring-0 sm:p-9"
        >
          <p className="text-2xl font-semibold tracking-[-0.03em]">
            Pemeriksaan berbasis bukti, sebelum pengajuan
          </p>
          <ol ref={listRef} className="relative mt-7 flex flex-col gap-6 pl-1">
            <span
              aria-hidden="true"
              className="absolute top-3 bottom-3 left-[1.15rem] w-px bg-brand/15"
            />
            <span
              ref={lineRef}
              aria-hidden="true"
              className="absolute top-3 bottom-3 left-[1.15rem] w-px origin-top bg-brand"
            />
            {SOLUTION_STEPS.map((step, index) => (
              <li key={step} className="relative flex items-start gap-4">
                <span className="relative z-10 grid size-9 shrink-0 place-items-center rounded-full bg-white text-sm font-semibold text-brand ring-1 ring-brand/20">
                  {index + 1}
                </span>
                <p className="pt-1.5 text-[0.95rem] leading-relaxed text-ink">{step}</p>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      <p
        data-reveal
        className="mt-8 flex items-start gap-3 rounded-2xl bg-surface-2 p-5 text-sm leading-relaxed text-muted-foreground ring-1 ring-line"
      >
        <InfoIcon className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true" />
        <span>
          <strong className="font-semibold text-ink">Batas informasi.</strong>{" "}
          Dampak seperti berkurangnya pending claim dan efisiensi biaya adalah
          manfaat yang diharapkan, bukan hasil yang sudah terbukti.
        </span>
      </p>
    </SectionShell>
  );
}

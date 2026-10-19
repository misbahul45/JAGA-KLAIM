"use client";

import { InfoIcon, ShieldCheckIcon } from "lucide-react";
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
              start: "top 75%",
              end: "bottom 65%",
              scrub: 0.5,
            },
          },
        );

        const steps = gsap.utils.toArray<HTMLElement>(
          "[data-solution-step]",
          list,
        );

        gsap.fromTo(
          steps,
          {
            y: 12,
            autoAlpha: 0.65,
          },
          {
            y: 0,
            autoAlpha: 1,
            duration: 0.5,
            stagger: 0.1,
            ease: "power2.out",
            scrollTrigger: {
              trigger: list,
              start: "top 75%",
              once: true,
            },
          },
        );
      });

      return () => mm.revert();
    },
    { scope: sectionRef },
  );

  return (
    <SectionShell id="masalah" ref={sectionRef}>
      <SectionHeading
        id="masalah"
        title="Temukan ketidaksesuaian sebelum klaim diajukan."
        lead="Setelah coding dan grouping INA-CBG, JAGA-KLAIM membantu memeriksa kesesuaian kode dengan bukti yang tersedia sebelum klaim diajukan. Tujuannya adalah membantu petugas menemukan hal yang perlu ditinjau lebih awal."
      />

      <div
        data-reveal-group
        className="mt-10 grid items-stretch gap-5 lg:grid-cols-2 lg:gap-6"
      >
        {/* Problem card */}
        <Card
          data-reveal-item
          className="gap-0 rounded-3xl bg-white p-6 ring-1 ring-line sm:p-8"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ruby">
              Tantangan
            </p>

            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
              Apa yang perlu diperiksa?
            </h3>

            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Beberapa hal dapat membuat pemeriksaan kesesuaian klaim
              membutuhkan waktu dan perhatian ekstra.
            </p>
          </div>

          <ul className="mt-7 flex flex-col gap-6">
            {PROBLEMS.map(({ icon: Icon, title, text }, index) => (
              <li key={title} className="flex items-start gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-ruby/10 text-ruby">
                  <Icon className="size-5" aria-hidden="true" />
                </span>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-semibold leading-snug text-ink">
                      {title}
                    </h4>

                    <span className="text-xs font-medium tabular-nums text-muted-foreground">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                  </div>

                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {text}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* Solution card */}
        <Card
          data-reveal-item
          className="gap-0 rounded-3xl bg-bento-lavender p-6 ring-0 sm:p-8"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">
              Solusi
            </p>

            <h3 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
              Lima langkah pemeriksaan
            </h3>

            <p className="mt-2 text-sm leading-relaxed text-ink/70">
              Dari penentuan bukti hingga peninjauan oleh petugas yang
              berwenang.
            </p>
          </div>

          <ol
            ref={listRef}
            aria-label="Lima langkah pemeriksaan JAGA-KLAIM"
            className="relative mt-8 flex flex-col gap-6"
          >
            {/* Background timeline */}
            <span
              aria-hidden="true"
              className="absolute bottom-4 left-[1.1rem] top-4 w-px bg-brand/15"
            />

            {/* Animated timeline */}
            <span
              ref={lineRef}
              aria-hidden="true"
              className="absolute bottom-4 left-[1.1rem] top-4 w-px origin-top bg-brand"
            />

            {SOLUTION_STEPS.map((step, index) => (
              <li
                key={step}
                data-solution-step
                className="relative flex items-start gap-4"
              >
                <span className="relative z-10 grid size-9 shrink-0 place-items-center rounded-full bg-white text-sm font-semibold tabular-nums text-brand ring-1 ring-brand/20">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <p className="min-w-0 flex-1 pt-1.5 text-sm leading-relaxed text-ink sm:text-[0.95rem]">
                  {step}
                </p>
              </li>
            ))}
          </ol>

          <div className="mt-8 flex items-start gap-3 rounded-2xl bg-white/70 p-4 ring-1 ring-brand/10">
            <ShieldCheckIcon
              className="mt-0.5 size-5 shrink-0 text-brand"
              aria-hidden="true"
            />

            <div>
              <p className="text-sm font-semibold text-ink">
                Keputusan tetap di tangan petugas
              </p>

              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                AI membantu menyajikan temuan. Koder atau verifikator tetap
                meninjau bukti dan menentukan tindak lanjut.
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Transparency note */}
      <p
        data-reveal
        className="mt-6 flex items-start gap-3 rounded-2xl bg-surface-2 p-4 text-sm leading-relaxed text-muted-foreground ring-1 ring-line sm:p-5"
      >
        <InfoIcon
          className="mt-0.5 size-4 shrink-0 text-brand"
          aria-hidden="true"
        />

        <span>
          <strong className="font-semibold text-ink">
            Catatan transparansi.
          </strong>{" "}
          Pengurangan klaim tertunda dan efisiensi biaya merupakan manfaat yang
          diharapkan. Dampak tersebut perlu diuji dan divalidasi menggunakan
          data operasional sebelum dapat dinyatakan sebagai hasil.
        </span>
      </p>
    </SectionShell>
  );
}

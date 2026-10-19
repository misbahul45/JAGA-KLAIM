"use client";

import {
  ArrowRightIcon,
  BanIcon,
  CircleCheckIcon,
} from "lucide-react";
import { useRef } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/use-reveal";

import {
  AI_LIMITS,
  AUTHORITY_FLOW,
  AUTHORITY_POINTS,
  EVIDENCE_TERMS,
} from "./data";
import { EvidenceComparison } from "./evidence-comparison";
import { InvestigationTimeline } from "./investigation-timeline";

export function EvidenceAuthority() {
  const sectionRef = useRef<HTMLElement>(null);

  useReveal(sectionRef);

  return (
    <SectionShell id="bukti" ref={sectionRef}>
      <SectionHeading
        id="bukti"
        title="Temuan berbasis bukti. Keputusan oleh manusia."
        lead="JAGA-KLAIM membandingkan bukti yang dibutuhkan dengan bukti yang ditemukan. Koder dan verifikator memeriksa hasilnya sebelum mengambil keputusan."
      />

      <div className="mt-10 grid gap-5 lg:mt-12 lg:grid-cols-2 lg:gap-6">
        <Card
          data-reveal
          className="gap-7 rounded-3xl bg-surface-2 p-6 ring-0 sm:p-8"
        >
          <div>
            <h3 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
              Cara bukti diperiksa
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Setiap temuan ditelusuri ke sumber yang mendukungnya.
            </p>
          </div>

          <dl className="grid gap-4">
            {EVIDENCE_TERMS.map((item) => (
              <div
                key={item.term}
                className="grid gap-1 border-b border-line/70 pb-3 last:border-0 last:pb-0 sm:grid-cols-[10.5rem_minmax(0,1fr)] sm:gap-4"
              >
                <dt className="text-sm font-semibold text-ink">
                  {item.term}
                </dt>
                <dd className="text-sm leading-relaxed text-muted-foreground">
                  {item.text}
                </dd>
              </div>
            ))}
          </dl>

          <EvidenceComparison />

          <div className="border-t border-line/70 pt-6">
            <h4 className="mb-5 text-lg font-semibold text-ink">
              Tahapan pemeriksaan
            </h4>
            <InvestigationTimeline />
          </div>
        </Card>

        <div className="flex flex-col gap-5">
          <Card
            data-reveal
            className="gap-0 rounded-3xl bg-bento-lavender p-6 ring-0 sm:p-8"
          >
            <h3 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
              Manusia tetap memegang keputusan
            </h3>

            <ul className="mt-6 flex flex-col gap-4">
              {AUTHORITY_POINTS.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <CircleCheckIcon
                    className="mt-0.5 size-5 shrink-0 text-brand"
                    aria-hidden="true"
                  />
                  <span className="text-sm leading-relaxed text-ink sm:text-base">
                    {point}
                  </span>
                </li>
              ))}
            </ul>

            <ol
              aria-label="Alur penilaian verifikator"
              className="mt-7 flex flex-wrap items-center gap-x-2 gap-y-3"
            >
              {AUTHORITY_FLOW.map((step, index) => (
                <li
                  key={step}
                  className="flex items-center gap-2"
                >
                  <span className="rounded-full bg-white px-3 py-2 text-xs font-medium text-ink ring-1 ring-brand/15 sm:text-sm">
                    {step}
                  </span>

                  {index < AUTHORITY_FLOW.length - 1 && (
                    <ArrowRightIcon
                      className="size-4 shrink-0 text-brand"
                      aria-hidden="true"
                    />
                  )}
                </li>
              ))}
            </ol>
          </Card>

          <Card
            data-reveal
            className="gap-0 rounded-3xl bg-night p-6 text-white ring-0 sm:p-8"
          >
            <h3 className="text-xl font-semibold tracking-tight sm:text-2xl">
              Batas kewenangan AI
            </h3>

            <p className="mt-2 text-sm leading-relaxed text-white/70">
              AI membantu pemeriksaan, bukan menggantikan keputusan manusia.
            </p>

            <ul className="mt-6 flex flex-col gap-4">
              {AI_LIMITS.map((limit) => (
                <li key={limit} className="flex items-start gap-3">
                  <BanIcon
                    className="mt-0.5 size-5 shrink-0 text-orange"
                    aria-hidden="true"
                  />
                  <span className="text-sm leading-relaxed text-white/85 sm:text-base">
                    {limit}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </SectionShell>
  );
}
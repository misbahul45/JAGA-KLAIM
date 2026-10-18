"use client";

import { ArrowRightIcon, BanIcon, CircleCheckIcon } from "lucide-react";
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
        title="Temuan yang bisa diperiksa, keputusan yang tetap milik manusia."
        lead="JAGA-KLAIM membandingkan bukti yang seharusnya ada dengan bukti yang ditemukan, menampilkan dasarnya, lalu menyerahkan keputusan kepada koder dan verifikator."
      />

      <div className="mt-14 grid gap-6 lg:grid-cols-2">
        <Card data-reveal className="gap-8 rounded-3xl bg-surface-2 p-7 text-base ring-0 sm:p-9">
          <p className="text-2xl font-semibold tracking-[-0.03em] text-ink">
            Investigasi yang mengutamakan bukti
          </p>
          <dl className="flex flex-col gap-4">
            {EVIDENCE_TERMS.map((item) => (
              <div key={item.term} className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
                <dt className="font-semibold text-ink sm:w-44 sm:shrink-0">{item.term}</dt>
                <dd className="text-muted-foreground">{item.text}</dd>
              </div>
            ))}
          </dl>
          <EvidenceComparison />
          <InvestigationTimeline />
        </Card>

        <div className="flex flex-col gap-6">
          <Card data-reveal className="gap-0 rounded-3xl bg-bento-lavender p-7 text-base ring-0 sm:p-9">
            <p className="text-2xl font-semibold tracking-[-0.03em] text-ink">
              Kewenangan ada pada manusia
            </p>
            <ul className="mt-6 flex flex-col gap-4">
              {AUTHORITY_POINTS.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <CircleCheckIcon
                    className="mt-0.5 size-5 shrink-0 text-brand"
                    aria-hidden="true"
                  />
                  <span className="leading-relaxed text-ink">{point}</span>
                </li>
              ))}
            </ul>
            <ol className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-3 text-sm font-medium text-ink">
              {AUTHORITY_FLOW.map((step, index) => (
                <li key={step} className="flex items-center gap-2">
                  <span className="rounded-full bg-white px-4 py-2 ring-1 ring-brand/15">
                    {step}
                  </span>
                  {index < AUTHORITY_FLOW.length - 1 ? (
                    <ArrowRightIcon className="size-4 text-brand" aria-hidden="true" />
                  ) : null}
                </li>
              ))}
            </ol>
          </Card>

          <Card data-reveal className="gap-0 rounded-3xl bg-night p-7 text-base text-white ring-0 sm:p-9">
            <p className="text-2xl font-semibold tracking-[-0.03em]">
              Batas kewenangan AI
            </p>
            <ul className="mt-6 flex flex-col gap-4">
              {AI_LIMITS.map((limit) => (
                <li key={limit} className="flex items-start gap-3">
                  <BanIcon className="mt-0.5 size-5 shrink-0 text-orange" aria-hidden="true" />
                  <span className="leading-relaxed text-white/85">{limit}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </SectionShell>
  );
}

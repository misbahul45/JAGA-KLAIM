"use client";

import { CheckIcon } from "lucide-react";
import { useRef } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/use-reveal";

import { GOVERNANCE_BLOCKS } from "./data";

export function Governance() {
  const sectionRef = useRef<HTMLElement>(null);

  useReveal(sectionRef);

  return (
    <SectionShell id="tata-kelola" tone="tint" ref={sectionRef}>
      <SectionHeading
        id="tata-kelola"
        title="Dapat ditelusuri, dilindungi, dan dievaluasi secara jujur."
        lead="Kepercayaan dibangun dari tata kelola yang jelas, perlindungan data, manfaat yang diharapkan, dan status pengembangan yang sebenarnya."
      />

      <ul data-reveal-group className="mt-14 grid gap-5 md:grid-cols-2">
        {GOVERNANCE_BLOCKS.map(({ icon: Icon, title, surface, points, note }) => (
          <li key={title} data-reveal-item className="flex">
            <Card
              className={`${surface} w-full gap-6 rounded-3xl p-7 text-base ring-0 sm:p-9`}
            >
            <span className="grid size-12 place-items-center rounded-2xl bg-ink text-white">
              <Icon className="size-6" aria-hidden="true" />
            </span>
            <p className="text-2xl font-semibold tracking-[-0.03em] text-ink">{title}</p>
            <ul className="flex flex-col gap-3">
              {points.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <CheckIcon className="mt-1 size-4 shrink-0 text-ink" aria-hidden="true" />
                  <span className="text-[0.95rem] leading-relaxed text-ink/85">{point}</span>
                </li>
              ))}
            </ul>
            {note ? (
              <p className="mt-auto rounded-2xl bg-white/70 p-4 text-sm leading-relaxed text-ink/80">
                {note}
              </p>
            ) : null}
            </Card>
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}

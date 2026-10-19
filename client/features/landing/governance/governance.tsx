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
        title="Transparan, aman, dan siap divalidasi."
        lead="Setiap temuan dapat ditelusuri, data dilindungi, dan manfaat dievaluasi sebelum diterapkan."
      />

      <ul
        data-reveal-group
        className="mt-10 grid gap-5 md:grid-cols-2"
      >
        {GOVERNANCE_BLOCKS.map(
          ({ icon: Icon, title, surface, points, note }) => (
            <li key={title} data-reveal-item className="flex">
              <Card
                className={`${surface} flex w-full flex-col gap-5 rounded-3xl p-6 ring-0 sm:p-8`}
              >
                <span className="grid size-11 place-items-center rounded-xl bg-ink text-white">
                  <Icon className="size-5" aria-hidden="true" />
                </span>

                <h3 className="text-xl font-semibold tracking-tight text-ink">
                  {title}
                </h3>

                <ul className="flex flex-col gap-3">
                  {points.map((point) => (
                    <li key={point} className="flex items-start gap-3">
                      <CheckIcon
                        className="mt-1 size-4 shrink-0 text-ink"
                        aria-hidden="true"
                      />
                      <span className="text-sm leading-relaxed text-ink/85">
                        {point}
                      </span>
                    </li>
                  ))}
                </ul>

                {note && (
                  <p className="mt-auto rounded-xl bg-white/70 p-4 text-sm leading-relaxed text-ink/75">
                    {note}
                  </p>
                )}
              </Card>
            </li>
          ),
        )}
      </ul>
    </SectionShell>
  );
}

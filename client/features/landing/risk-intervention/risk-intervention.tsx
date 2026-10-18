"use client";

import { InfoIcon } from "lucide-react";
import { useRef } from "react";

import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/use-reveal";

import { RISK_VECTORS } from "./data";
import { TierExplorer } from "./tier-explorer";

export function RiskIntervention() {
  const sectionRef = useRef<HTMLElement>(null);

  useReveal(sectionRef);

  return (
    <SectionShell id="risiko" tone="tint" ref={sectionRef}>
      <SectionHeading
        id="risiko"
        title="Tiga vektor risiko, empat tingkat intervensi."
        lead="Cakupan awal JAGA-KLAIM adalah tiga vektor risiko berikut. Ini bukan klaim bahwa seluruh kasus sudah dapat dideteksi."
      />

      <ul data-reveal-group className="mt-14 grid gap-5 md:grid-cols-3">
        {RISK_VECTORS.map(({ icon: Icon, name, focus, surface }) => (
          <li key={name} data-reveal-item className="flex">
            <Card
              className={`${surface} w-full gap-10 rounded-3xl p-7 text-base ring-0 sm:p-8`}
            >
              <span className="grid size-12 place-items-center rounded-2xl bg-ink text-white">
                <Icon className="size-6" aria-hidden="true" />
              </span>
              <div>
                <p className="text-2xl font-semibold tracking-[-0.03em] text-ink">
                  {name}
                </p>
                <p className="mt-3 text-[0.95rem] leading-relaxed text-ink/75">{focus}</p>
              </div>
            </Card>
          </li>
        ))}
      </ul>

      <div data-reveal className="mt-16">
        <p className="mb-6 max-w-2xl text-2xl font-semibold tracking-[-0.03em] text-ink">
          Respons sistem bersifat bertingkat.
        </p>
        <TierExplorer />
      </div>

      <p
        data-reveal
        className="mt-8 flex items-start gap-3 rounded-2xl bg-white p-5 text-sm leading-relaxed text-muted-foreground ring-1 ring-line"
      >
        <InfoIcon className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true" />
        <span>
          Intervensi bersifat bertingkat, abstain adalah bagian dari desain, dan
          tidak semua temuan harus menghasilkan alert yang mengganggu.
        </span>
      </p>
    </SectionShell>
  );
}

"use client";

import { ArrowRightIcon } from "lucide-react";
import { useRef } from "react";

import { ButtonLink } from "@/components/shared/button-link";
import { SectionHeading } from "@/components/shared/section-heading";
import { SectionShell } from "@/components/shared/section-shell";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useReveal } from "@/hooks/use-reveal";

import { FAQ_ITEMS } from "./data";

export function FaqCta() {
  const sectionRef = useRef<HTMLElement>(null);

  useReveal(sectionRef);

  return (
    <SectionShell id="faq" ref={sectionRef}>
      <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <SectionHeading
          id="faq"
          title="Pertanyaan yang sering diajukan."
          lead="Jawaban singkat tentang cara kerja, batas kewenangan AI, audit, dan privasi."
          className="lg:sticky lg:top-28 lg:self-start"
        />

        <Accordion data-reveal-group className="border-t border-line">
          {FAQ_ITEMS.map((item) => (
            <AccordionItem
              key={item.question}
              data-reveal-item
              value={item.question}
              className="border-b border-line"
            >
              <AccordionTrigger className="rounded-none border-0 py-5 text-lg font-semibold tracking-[-0.02em] text-ink hover:no-underline">
                {item.question}
              </AccordionTrigger>
              <AccordionContent className="text-base leading-relaxed text-muted-foreground">
                {item.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>

      <div
        data-reveal
        className="relative mt-24 overflow-hidden rounded-[2rem] bg-night px-7 py-14 text-white sm:px-14 sm:py-20"
      >
        <div aria-hidden="true" className="bg-dots-light absolute inset-0" />
        <div className="relative flex max-w-2xl flex-col items-start gap-6">
          <h2 className="text-4xl leading-[1.06] font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
            Mulai dari memahami cara kerjanya.
          </h2>
          <p className="text-lg leading-relaxed text-white/70">
            Pelajari alur tujuh tahap dan batas kewenangan AI, lalu telusuri
            bagaimana bukti, audit, dan keputusan manusia saling terhubung.
            Prototipe publik dan kanal pilot belum tersedia saat ini.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <ButtonLink href="#cara-kerja" variant="light" size="xl">
              Pelajari Cara Kerja
              <ArrowRightIcon data-icon="inline-end" />
            </ButtonLink>
            <ButtonLink href="#bukti" variant="glass" size="xl">
              Jelajahi Arsitektur
            </ButtonLink>
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

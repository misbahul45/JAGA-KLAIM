"use client";

import { useRef, useState } from "react";

import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { gsap, MOTION_OK, useGSAP } from "@/lib/gsap";
import { cn } from "@/lib/utils";

import { TIERS } from "./data";

export function TierExplorer() {
  const rootRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState<string>(TIERS[0].code);
  const tier = TIERS.find((item) => item.code === active) ?? TIERS[0];

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        gsap.fromTo(
          "[data-meter-bar]",
          { scaleY: 0 },
          {
            scaleY: 1,
            duration: 0.6,
            ease: "power3.out",
            stagger: 0.07,
            overwrite: "auto",
          },
        );
        gsap.fromTo(
          "[data-tier-copy]",
          { y: 14, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, duration: 0.5, ease: "power3.out", clearProps: "all" },
        );
      });
    },
    { scope: rootRef, dependencies: [active] },
  );

  return (
    <div ref={rootRef}>
      <Tabs value={active} onValueChange={(value) => setActive(String(value))}>
        <TabsList
          aria-label="Tingkat intervensi"
          className="h-auto w-full flex-wrap justify-start gap-2 rounded-none bg-transparent p-0"
        >
          {TIERS.map((item) => (
            <TabsTrigger
              key={item.code}
              value={item.code}
              className={cn(
                "h-11 flex-none rounded-full border-line bg-white px-5 text-sm font-medium text-ink ring-0 hover:bg-lavender",
                "data-active:border-ink data-active:bg-ink data-active:text-white",
                "after:hidden",
              )}
            >
              {item.code} · {item.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {TIERS.map((item) => (
          <TabsContent key={item.code} value={item.code} className="mt-6">
            <Card className="grid gap-8 rounded-3xl bg-white p-7 text-base ring-1 ring-line sm:p-10 md:grid-cols-[1.4fr_1fr] md:items-end">
              <div data-tier-copy className="flex flex-col gap-4">
                <p className="text-3xl font-semibold tracking-[-0.035em] text-ink sm:text-4xl">
                  {item.code} {item.name}
                </p>
                <p className="text-lg leading-relaxed text-ink">{item.summary}</p>
                <p className="text-base leading-relaxed text-muted-foreground">
                  {item.detail}
                </p>
              </div>

              <div
                role="img"
                aria-label={`Tingkat intervensi ${item.level} dari ${TIERS.length}`}
                className="flex h-32 items-end gap-3"
              >
                {TIERS.map((bar) => (
                  <span
                    key={bar.code}
                    data-meter-bar
                    style={{ height: `${bar.level * 25}%` }}
                    className={cn(
                      "w-full origin-bottom rounded-xl",
                      bar.level <= tier.level ? tier.color : "bg-surface-2",
                    )}
                  />
                ))}
              </div>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

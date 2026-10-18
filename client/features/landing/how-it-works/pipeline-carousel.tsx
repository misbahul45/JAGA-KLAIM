"use client";

import { ChevronLeftIcon, ChevronRightIcon, PauseIcon, PlayIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  type CarouselApi,
} from "@/components/ui/carousel";
import { gsap, MOTION_OK, ScrollTrigger, useGSAP } from "@/lib/gsap";

import { STAGES } from "./data";

type PipelineCarouselProps = {
  onActiveChange: (index: number) => void;
};

const AUTOPLAY_SECONDS = 5.5;

export function PipelineCarousel({ onActiveChange }: PipelineCarouselProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLSpanElement>(null);
  const syncRef = useRef<(() => void) | null>(null);
  const playingRef = useRef(true);
  const [api, setApi] = useState<CarouselApi>();
  const [playing, setPlaying] = useState(true);
  const [edge, setEdge] = useState({ start: true, end: false });
  const [motionOk, setMotionOk] = useState(false);

  useEffect(() => {
    if (!api) return;
    const onSelect = () => {
      onActiveChange(api.selectedScrollSnap());
      setEdge({ start: !api.canScrollPrev(), end: !api.canScrollNext() });
    };
    api.on("select", onSelect);
    api.on("reInit", onSelect);
    return () => {
      api.off("select", onSelect);
      api.off("reInit", onSelect);
    };
  }, [api, onActiveChange]);

  useGSAP(
    () => {
      if (!api) return;
      const root = rootRef.current;
      if (!root) return;
      const mm = gsap.matchMedia();

      mm.add(MOTION_OK, () => {
        setMotionOk(true);
        const cards = gsap.utils.toArray<HTMLElement>("[data-stage-card]", root);
        let visible = false;
        let hovered = false;

        const focus = () => {
          const current = api.selectedScrollSnap();
          cards.forEach((card, index) => {
            gsap.to(card, {
              scale: index === current ? 1 : 0.94,
              opacity: index === current ? 1 : 0.5,
              duration: 0.5,
              ease: "power3.out",
              overwrite: "auto",
            });
          });
        };

        const progress = gsap.fromTo(
          barRef.current,
          { scaleX: 0 },
          {
            scaleX: 1,
            duration: AUTOPLAY_SECONDS,
            ease: "none",
            paused: true,
            onComplete: () => {
              if (api.canScrollNext()) api.scrollNext();
              else api.scrollTo(0);
            },
          },
        );

        const sync = () => {
          if (visible && !hovered && playingRef.current) progress.play();
          else progress.pause();
        };
        syncRef.current = sync;

        const onSelect = () => {
          progress.progress(0);
          focus();
          sync();
        };
        const onEnter = () => {
          hovered = true;
          sync();
        };
        const onLeave = () => {
          hovered = false;
          sync();
        };

        focus();
        api.on("select", onSelect);
        api.on("reInit", onSelect);
        root.addEventListener("pointerenter", onEnter);
        root.addEventListener("pointerleave", onLeave);
        root.addEventListener("focusin", onEnter);
        root.addEventListener("focusout", onLeave);

        const trigger = ScrollTrigger.create({
          trigger: root,
          start: "top 85%",
          end: "bottom 15%",
          onToggle: (self) => {
            visible = self.isActive;
            sync();
          },
        });

        gsap.from(cards, {
          y: 36,
          autoAlpha: 0,
          duration: 0.8,
          ease: "power3.out",
          stagger: 0.08,
          clearProps: "visibility",
          scrollTrigger: { trigger: root, start: "top 85%", once: true },
        });

        return () => {
          setMotionOk(false);
          syncRef.current = null;
          trigger.kill();
          api.off("select", onSelect);
          api.off("reInit", onSelect);
          root.removeEventListener("pointerenter", onEnter);
          root.removeEventListener("pointerleave", onLeave);
          root.removeEventListener("focusin", onEnter);
          root.removeEventListener("focusout", onLeave);
        };
      });
    },
    { scope: rootRef, dependencies: [api] },
  );

  function togglePlaying() {
    const next = !playingRef.current;
    playingRef.current = next;
    setPlaying(next);
    syncRef.current?.();
  }

  return (
    <div ref={rootRef}>
      <Carousel
        setApi={setApi}
        opts={{ align: "center", containScroll: false }}
        aria-label="Tujuh tahap pipeline JAGA-KLAIM"
      >
        <CarouselContent className="-ml-4 py-2">
          {STAGES.map((stage, index) => {
            const Icon = stage.icon;
            return (
              <CarouselItem
                key={stage.name}
                className="basis-[86%] pl-4 sm:basis-[52%] lg:basis-[36%]"
                aria-label={`Tahap ${index + 1} dari ${STAGES.length}: ${stage.name}`}
              >
                <article
                  data-stage-card
                  className="flex h-full flex-col gap-5 rounded-3xl bg-white/[0.06] p-7 ring-1 ring-white/12"
                >
                  <div className="flex items-start justify-between">
                    <span className="grid size-12 place-items-center rounded-2xl bg-brand text-white">
                      <Icon className="size-6" aria-hidden="true" />
                    </span>
                    <span
                      aria-hidden="true"
                      className="font-mono text-5xl leading-none font-medium text-white/15"
                    >
                      {index + 1}
                    </span>
                  </div>
                  <div>
                    <p className="text-xl font-semibold tracking-[-0.025em] text-white">
                      {stage.name}
                    </p>
                    <p className="mt-2 text-[0.95rem] leading-relaxed text-white/70">
                      {stage.description}
                    </p>
                  </div>
                </article>
              </CarouselItem>
            );
          })}
        </CarouselContent>
      </Carousel>

      <div className="mt-6 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Button
            variant="glass"
            size="icon-lg"
            aria-label="Tahap sebelumnya"
            disabled={edge.start}
            onClick={() => api?.scrollPrev()}
          >
            <ChevronLeftIcon />
          </Button>
          <Button
            variant="glass"
            size="icon-lg"
            aria-label="Tahap berikutnya"
            disabled={edge.end}
            onClick={() => api?.scrollNext()}
          >
            <ChevronRightIcon />
          </Button>
        </div>
        <div
          aria-hidden="true"
          className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/10"
        >
          <span
            ref={barRef}
            className="absolute inset-0 origin-left scale-x-0 rounded-full bg-brand"
          />
        </div>
        {motionOk ? (
          <Button
            variant="glass"
            size="icon-lg"
            aria-pressed={!playing}
            aria-label={playing ? "Jeda putar otomatis" : "Lanjutkan putar otomatis"}
            onClick={togglePlaying}
          >
            {playing ? <PauseIcon /> : <PlayIcon />}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

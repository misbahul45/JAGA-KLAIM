"use client";

import {
  ChevronLeftIcon,
  ChevronRightIcon,
  PauseIcon,
  PlayIcon,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

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

const AUTOPLAY_SECONDS = 6;

export function PipelineCarousel({
  onActiveChange,
}: PipelineCarouselProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLSpanElement>(null);
  const syncRef = useRef<(() => void) | null>(null);
  const playingRef = useRef(true);

  const [api, setApi] = useState<CarouselApi>();
  const [selected, setSelected] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [edge, setEdge] = useState({ start: true, end: false });
  const [motionOk, setMotionOk] = useState(false);

  const handleSelect = useCallback(() => {
    if (!api) return;

    const index = api.selectedScrollSnap();

    setSelected(index);
    setEdge({
      start: !api.canScrollPrev(),
      end: !api.canScrollNext(),
    });

    onActiveChange(index);
  }, [api, onActiveChange]);

  useEffect(() => {
    if (!api) return;

    handleSelect();

    api.on("select", handleSelect);
    api.on("reInit", handleSelect);

    return () => {
      api.off("select", handleSelect);
      api.off("reInit", handleSelect);
    };
  }, [api, handleSelect]);

  useGSAP(
    () => {
      const root = rootRef.current;
      const bar = barRef.current;

      if (!api || !root || !bar) return;

      const mm = gsap.matchMedia();

      mm.add(MOTION_OK, () => {
        setMotionOk(true);

        const cards = gsap.utils.toArray<HTMLElement>(
          "[data-stage-card]",
          root,
        );

        let visible = false;
        let hovered = false;
        let focused = false;

        const progress = gsap.fromTo(
          bar,
          { scaleX: 0 },
          {
            scaleX: 1,
            duration: AUTOPLAY_SECONDS,
            ease: "none",
            paused: true,
            onComplete: () => {
              if (api.canScrollNext()) {
                api.scrollNext();
              } else {
                api.scrollTo(0);
              }
            },
          },
        );

        const sync = () => {
          if (visible && !hovered && !focused && playingRef.current) {
            progress.play();
          } else {
            progress.pause();
          }
        };

        syncRef.current = sync;

        const focusCards = () => {
          const current = api.selectedScrollSnap();

          cards.forEach((card, index) => {
            gsap.to(card, {
              scale: index === current ? 1 : 0.97,
              duration: 0.4,
              ease: "power2.out",
              overwrite: "auto",
            });
          });
        };

        const onSelect = () => {
          progress.pause();
          progress.progress(0);
          focusCards();
          sync();
        };

        const onPointerEnter = () => {
          hovered = true;
          sync();
        };

        const onPointerLeave = () => {
          hovered = false;
          sync();
        };

        const onFocusIn = () => {
          focused = true;
          sync();
        };

        const onFocusOut = (event: FocusEvent) => {
          const nextTarget = event.relatedTarget;

          if (nextTarget instanceof Node && root.contains(nextTarget)) {
            return;
          }

          focused = false;
          sync();
        };

        focusCards();

        api.on("select", onSelect);
        api.on("reInit", onSelect);

        root.addEventListener("pointerenter", onPointerEnter);
        root.addEventListener("pointerleave", onPointerLeave);
        root.addEventListener("focusin", onFocusIn);
        root.addEventListener("focusout", onFocusOut);

        const trigger = ScrollTrigger.create({
          trigger: root,
          start: "top 85%",
          end: "bottom 15%",
          onToggle: (self) => {
            visible = self.isActive;
            sync();
          },
        });

        gsap.fromTo(
          cards,
          { y: 18, autoAlpha: 0 },
          {
            y: 0,
            autoAlpha: 1,
            duration: 0.65,
            stagger: 0.07,
            ease: "power2.out",
            clearProps: "opacity,visibility",
            scrollTrigger: {
              trigger: root,
              start: "top 85%",
              once: true,
            },
          },
        );

        return () => {
          syncRef.current = null;
          setMotionOk(false);

          progress.kill();
          trigger.kill();

          api.off("select", onSelect);
          api.off("reInit", onSelect);

          root.removeEventListener("pointerenter", onPointerEnter);
          root.removeEventListener("pointerleave", onPointerLeave);
          root.removeEventListener("focusin", onFocusIn);
          root.removeEventListener("focusout", onFocusOut);
        };
      });

      return () => mm.revert();
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
        opts={{
          align: "center",
          containScroll: false,
          duration: 35,
        }}
        aria-label="Tujuh tahap pipeline JAGA-KLAIM"
      >
        <CarouselContent className="-ml-4 py-3">
          {STAGES.map((stage, index) => {
            const Icon = stage.icon;
            const isSelected = selected === index;

            return (
              <CarouselItem
                key={stage.name}
                className="basis-[88%] pl-4 sm:basis-[55%] lg:basis-[36%]"
                aria-label={`Tahap ${index + 1} dari ${STAGES.length}: ${stage.name}`}
              >
                <button
                  type="button"
                  data-stage-card
                  aria-current={isSelected ? "step" : undefined}
                  onClick={() => api?.scrollTo(index)}
                  className={`flex h-full min-h-[220px] w-full flex-col rounded-2xl p-6 text-left ring-1 outline-none transition-[background-color,ring-color] duration-300 focus-visible:ring-2 focus-visible:ring-mint ${
                    isSelected
                      ? "bg-white/[0.10] ring-mint/50"
                      : "bg-white/[0.04] ring-white/10 hover:bg-white/[0.07]"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <span
                      className={`grid size-11 place-items-center rounded-xl transition-colors duration-300 ${
                        isSelected
                          ? "bg-brand text-white"
                          : "bg-white/10 text-white/75"
                      }`}
                    >
                      <Icon className="size-5" aria-hidden="true" />
                    </span>

                    <span
                      aria-hidden="true"
                      className={`font-mono text-4xl font-medium leading-none transition-colors duration-300 ${
                        isSelected ? "text-mint/70" : "text-white/15"
                      }`}
                    >
                      {String(index + 1).padStart(2, "0")}
                    </span>
                  </div>

                  <div className="mt-6">
                    <h3 className="text-lg font-semibold tracking-tight text-white">
                      {stage.name}
                    </h3>

                    <p className="mt-2 text-sm leading-relaxed text-white/65">
                      {stage.description}
                    </p>
                  </div>

                  <div className="mt-auto flex items-center gap-2 pt-5">
                    <span
                      className={`h-1 rounded-full transition-all duration-300 ${
                        isSelected ? "w-8 bg-mint" : "w-3 bg-white/20"
                      }`}
                    />

                    <span className="text-xs text-white/40">
                      {isSelected ? "Tahap aktif" : "Pilih tahap"}
                    </span>
                  </div>
                </button>
              </CarouselItem>
            );
          })}
        </CarouselContent>
      </Carousel>

      <div className="mt-5 flex items-center gap-3 sm:gap-4">
        <div className="flex shrink-0 items-center gap-2">
          <Button
            variant="glass"
            size="icon-lg"
            aria-label="Tahap sebelumnya"
            disabled={edge.start}
            onClick={() => api?.scrollPrev()}
          >
            <ChevronLeftIcon aria-hidden="true" />
          </Button>

          <Button
            variant="glass"
            size="icon-lg"
            aria-label="Tahap berikutnya"
            disabled={edge.end}
            onClick={() => api?.scrollNext()}
          >
            <ChevronRightIcon aria-hidden="true" />
          </Button>
        </div>

        <div
          role="progressbar"
          aria-label="Progres putar otomatis"
          aria-valuemin={0}
          aria-valuemax={100}
          className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/10"
        >
          <span
            ref={barRef}
            aria-hidden="true"
            className="absolute inset-0 origin-left scale-x-0 rounded-full bg-mint"
          />
        </div>

        {motionOk && (
          <Button
            variant="glass"
            size="icon-lg"
            aria-pressed={playing}
            aria-label={
              playing
                ? "Jeda putar otomatis"
                : "Lanjutkan putar otomatis"
            }
            onClick={togglePlaying}
          >
            {playing ? (
              <PauseIcon aria-hidden="true" />
            ) : (
              <PlayIcon aria-hidden="true" />
            )}
          </Button>
        )}
      </div>

      <p className="sr-only" aria-live="polite" aria-atomic="true">
        Tahap {selected + 1} dari {STAGES.length}: {STAGES[selected]?.name}
      </p>
    </div>
  );
}
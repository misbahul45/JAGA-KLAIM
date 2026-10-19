"use client";

import { useRef } from "react";

import { ButtonLink } from "@/components/shared/button-link";
import { Logo } from "@/components/shared/logo";
import { ScrollTrigger, useGSAP } from "@/lib/gsap";

export function SiteHeader() {
  const headerRef = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const header = headerRef.current;

      if (!header) return;

      const updateHeader = (isScrolled: boolean) => {
        header.setAttribute("data-scrolled", String(isScrolled));
      };

      updateHeader(window.scrollY > 8);

      ScrollTrigger.create({
        trigger: document.documentElement,
        start: 8,
        end: "max",
        onUpdate: (self) => {
          updateHeader(self.scroll() > 8);
        },
        onRefresh: (self) => {
          updateHeader(self.scroll() > 8);
        },
      });
    },
    { scope: headerRef },
  );

  return (
    <header
      ref={headerRef}
      data-scrolled="false"
      className={[
        "fixed left-0 right-0 top-0 z-50 mx-auto",
        "w-full max-w-none",
        "border border-transparent",
        "bg-background",
        "transition-[top,width,max-width,border-radius,border-color,box-shadow,background-color]",
        "duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]",
        "data-[scrolled=true]:top-3",
        "data-[scrolled=true]:w-[calc(100%-2rem)]",
        "data-[scrolled=true]:max-w-5xl",
        "data-[scrolled=true]:rounded-2xl",
        "data-[scrolled=true]:border-line",
        "data-[scrolled=true]:bg-background/95",
        "data-[scrolled=true]:shadow-lg",
        "data-[scrolled=true]:backdrop-blur-xl",
        "motion-reduce:transition-none",
      ].join(" ")}
    >
      <div className="mx-auto flex h-16 w-full items-center justify-between gap-4 px-5 sm:px-8">
        <a
          href="#beranda"
          aria-label="JAGA-KLAIM, kembali ke bagian atas"
          className="shrink-0 rounded-full outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <Logo />
        </a>

        <nav
          aria-label="Navigasi utama"
          className="flex shrink-0 items-center gap-2"
        >
          <ButtonLink href="#cara-kerja" size="lg">
            Pelajari Cara Kerja
          </ButtonLink>

          <ButtonLink
            href="#bukti"
            variant="outline"
            size="lg"
            className="hidden sm:inline-flex"
          >
            Jelajahi Arsitektur
          </ButtonLink>
        </nav>
      </div>
    </header>
  );
}
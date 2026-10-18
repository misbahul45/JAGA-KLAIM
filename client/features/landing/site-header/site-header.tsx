"use client";

import { useRef } from "react";

import { ButtonLink } from "@/components/shared/button-link";
import { Logo } from "@/components/shared/logo";
import { ScrollTrigger, useGSAP } from "@/lib/gsap";

export function SiteHeader() {
  const headerRef = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      ScrollTrigger.create({
        start: 0,
        end: "max",
        onUpdate: (self) => {
          headerRef.current?.setAttribute(
            "data-scrolled",
            self.scroll() > 8 ? "true" : "false",
          );
        },
      });
    },
    { scope: headerRef },
  );

  return (
    <header
      ref={headerRef}
      data-scrolled="false"
      className="fixed inset-x-0 top-0 z-50 border-b border-transparent bg-background transition-colors duration-200 data-[scrolled=true]:border-line"
    >
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
        <a
          href="#beranda"
          aria-label="JAGA-KLAIM, kembali ke bagian atas"
          className="rounded-full outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <Logo />
        </a>

        <nav aria-label="Aksi utama" className="flex items-center gap-2">
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

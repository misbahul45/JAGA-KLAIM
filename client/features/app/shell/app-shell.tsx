"use client";

import { MenuIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

import { AccountMenu } from "./account-menu";
import { NavList } from "./nav-list";

const STATUS_NOTICE =
  "Prototipe pengembangan dengan data simulasi. Belum diuji di lingkungan rumah sakit.";

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6">
      <Logo />
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        <NavList onNavigate={onNavigate} />
      </div>
      <div className="space-y-3">
        <AccountMenu onNavigate={onNavigate} />
        <p className="text-[0.7rem] leading-snug text-muted-foreground">{STATUS_NOTICE}</p>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-1 bg-surface">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-line bg-white p-4 lg:block">
        <SidebarBody />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-white px-4 py-2.5 lg:hidden">
          <Logo />
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <SheetTrigger
              render={<Button variant="outline" size="icon" aria-label="Buka menu navigasi" />}
            >
              <MenuIcon aria-hidden="true" />
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-4">
              <SheetTitle className="sr-only">Menu navigasi</SheetTitle>
              <SheetDescription className="sr-only">
                Pilih halaman yang ingin dibuka.
              </SheetDescription>
              <SidebarBody onNavigate={() => setMenuOpen(false)} />
            </SheetContent>
          </Sheet>
        </header>

        <main id="konten-utama" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}

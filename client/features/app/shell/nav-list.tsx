"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { useAuth } from "../auth/auth-context";
import { GROUP_LABELS, GROUP_ORDER, isActive, visibleNav } from "./nav";

type NavListProps = {
  onNavigate?: () => void;
};

export function NavList({ onNavigate }: NavListProps) {
  const { can } = useAuth();
  const pathname = usePathname();
  const items = visibleNav(can);

  return (
    <nav aria-label="Navigasi utama" className="space-y-5">
      {GROUP_ORDER.map((group) => {
        const groupItems = items.filter((item) => item.group === group);
        if (groupItems.length === 0) return null;
        return (
          <div key={group}>
            <p className="px-3 pb-1.5 text-[0.7rem] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
              {GROUP_LABELS[group]}
            </p>
            <ul className="space-y-0.5">
              {groupItems.map((item) => {
                const active = isActive(pathname, item.href);
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                        active
                          ? "bg-lavender text-brand"
                          : "text-ink/80 hover:bg-surface-2 hover:text-ink",
                      )}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

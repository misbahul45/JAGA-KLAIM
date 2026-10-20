"use client";

import Link from "next/link";
import { LogOutIcon, UserIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

import { useAuth } from "../auth/auth-context";
import { ROLE_LABELS, labelOf } from "../shared/labels";

type AccountMenuProps = {
  onNavigate?: () => void;
};

export function AccountMenu({ onNavigate }: AccountMenuProps) {
  const { principal, signOut } = useAuth();
  return (
    <div className="space-y-2 rounded-2xl border border-line bg-white p-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-ink">{principal.name}</p>
        <p className="truncate text-xs text-muted-foreground">{principal.email}</p>
        <p className="mt-0.5 text-xs font-medium text-brand">{labelOf(ROLE_LABELS, principal.role)}</p>
      </div>
      <div className="flex gap-2">
        <Link
          href="/akun"
          onClick={onNavigate}
          className="inline-flex h-7 flex-1 items-center justify-center gap-1 rounded-full border border-border bg-background px-3 text-[0.8rem] font-medium hover:bg-muted"
        >
          <UserIcon className="size-3.5" aria-hidden="true" />
          Akun
        </Link>
        <Button variant="outline" size="sm" className="flex-1" onClick={() => void signOut()}>
          <LogOutIcon aria-hidden="true" />
          Keluar
        </Button>
      </div>
    </div>
  );
}

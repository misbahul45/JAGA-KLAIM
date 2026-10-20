"use client";

import { LockIcon } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/shared/empty-state";

import { useAuth } from "../auth/auth-context";

type RequirePermissionProps = {
  permission: string;
  children: ReactNode;
};

export function RequirePermission({ permission, children }: RequirePermissionProps) {
  const { can } = useAuth();
  if (!can(permission)) {
    return (
      <EmptyState
        icon={LockIcon}
        title="Akses ditolak"
        description="Peran Anda tidak memiliki izin untuk membuka halaman ini."
      />
    );
  }
  return <>{children}</>;
}

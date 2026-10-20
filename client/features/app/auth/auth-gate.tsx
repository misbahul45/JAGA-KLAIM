"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, type ReactNode } from "react";

import { ErrorNotice } from "@/components/shared/error-notice";
import { LoadingBlock } from "@/components/shared/loading-block";
import { useApi } from "@/hooks/use-api";
import { ApiRequestError, UNAUTHORIZED_EVENT, apiFetch } from "@/lib/api";
import type { Principal } from "@/lib/api-types";

import { AuthContext, type AuthValue } from "./auth-context";
import { loginUrl } from "./redirect";

export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data, error, reload } = useApi<Principal>("/v1/auth/me");
  const unauthorized = error instanceof ApiRequestError && error.status === 401;

  useEffect(() => {
    if (unauthorized) router.replace(loginUrl(pathname));
  }, [unauthorized, pathname, router]);

  useEffect(() => {
    const onUnauthorized = () => router.replace(loginUrl(pathname));
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [pathname, router]);

  const signOut = useCallback(async () => {
    try {
      await apiFetch("/v1/auth/logout", { method: "POST" });
    } finally {
      router.replace("/masuk");
    }
  }, [router]);

  const value = useMemo<AuthValue | null>(() => {
    if (!data) return null;
    const granted = new Set(data.permissions);
    return { principal: data, can: (permission) => granted.has(permission), signOut };
  }, [data, signOut]);

  if (value) return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;

  if (error && !unauthorized) {
    return (
      <div className="mx-auto w-full max-w-lg p-8">
        <ErrorNotice error={error} title="Tidak dapat memuat sesi" onRetry={reload} />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-lg p-8">
      <LoadingBlock rows={3} label="Memeriksa sesi" />
    </div>
  );
}

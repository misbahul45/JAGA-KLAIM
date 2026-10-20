import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import { LoadingBlock } from "@/components/shared/loading-block";
import { AuthGate } from "@/features/app/auth/auth-gate";
import { AppShell } from "@/features/app/shell/app-shell";

export const metadata: Metadata = {
  title: { default: "JAGA-KLAIM", template: "%s | JAGA-KLAIM" },
  robots: { index: false, follow: false },
};

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto w-full max-w-lg p-8">
          <LoadingBlock rows={4} label="Memuat aplikasi" />
        </div>
      }
    >
      <AuthGate>
        <AppShell>
          <Suspense fallback={<LoadingBlock rows={5} />}>{children}</Suspense>
        </AppShell>
      </AuthGate>
    </Suspense>
  );
}

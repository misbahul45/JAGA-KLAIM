import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/features/app/auth/login-form";

export const metadata: Metadata = {
  title: "Masuk | JAGA-KLAIM",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return (
    <main id="konten-utama" className="bg-dots flex flex-1 items-center justify-center bg-surface px-4 py-12">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}

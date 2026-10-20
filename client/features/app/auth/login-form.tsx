"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ErrorNotice } from "@/components/shared/error-notice";
import { Field } from "@/components/shared/field";
import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { Principal } from "@/lib/api-types";

import { defaultRoute } from "../shell/nav";
import { safeNext } from "./redirect";

async function signIn(email: string, password: string): Promise<Principal> {
  return apiFetch<Principal>("/v1/auth/login", { method: "POST", json: { email, password } });
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useAction(signIn);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const principal = await login.run(email.trim(), password);
    if (principal) router.replace(safeNext(params.get("lanjut")) ?? defaultRoute(principal.permissions));
  };

  return (
    <div className="w-full max-w-md space-y-6 rounded-3xl border border-line bg-white p-6 shadow-sm sm:p-8">
      <div className="space-y-2">
        <Logo />
        <h1 className="text-2xl font-semibold tracking-[-0.03em] text-ink">Masuk</h1>
        <p className="text-sm text-muted-foreground">
          Gunakan akun yang diberikan admin faskes Anda. Sesi berakhir otomatis dan setiap tindakan
          penting tercatat pada audit trail.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="email" label="Email">
          <Input
            id="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Field id="password" label="Kata sandi">
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <ErrorNotice error={login.error} title="Tidak dapat masuk" />
        <Button
          type="submit"
          variant="brand"
          size="xl"
          className="w-full"
          disabled={login.pending || !email.trim() || !password}
        >
          {login.pending ? "Memeriksa..." : "Masuk"}
        </Button>
      </form>

      <p className="text-xs text-muted-foreground">
        Prototipe pengembangan dengan data simulasi. Belum diuji di lingkungan rumah sakit.
      </p>
    </div>
  );
}

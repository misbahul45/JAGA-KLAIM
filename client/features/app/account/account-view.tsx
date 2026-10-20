"use client";

import { CheckCircle2Icon } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ErrorNotice } from "@/components/shared/error-notice";
import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";

import { useAuth } from "../auth/auth-context";
import { ROLE_LABELS, labelOf } from "../shared/labels";
import { KeyValueList } from "../shared/key-value";
import { SectionCard } from "../shared/section-card";

function ChangePasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saved, setSaved] = useState(false);
  const change = useAction(() =>
    apiFetch<{ message: string }>("/v1/auth/password", {
      method: "POST",
      json: { current_password: current, new_password: next },
    }),
  );
  const mismatch = confirm !== "" && confirm !== next;
  const ready = current !== "" && next.length >= 12 && confirm === next;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaved(false);
    const result = await change.run();
    if (result) {
      setSaved(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    }
  };

  return (
    <form onSubmit={submit} className="max-w-md space-y-4" noValidate>
      <Field id="pw-current" label="Kata sandi saat ini">
        <Input id="pw-current" type="password" autoComplete="current-password" value={current} onChange={(event) => setCurrent(event.target.value)} />
      </Field>
      <Field id="pw-new" label="Kata sandi baru" hint="Minimal 12 karakter, tidak diawali atau diakhiri spasi.">
        <Input id="pw-new" type="password" autoComplete="new-password" value={next} onChange={(event) => setNext(event.target.value)} />
      </Field>
      <Field id="pw-confirm" label="Ulangi kata sandi baru" error={mismatch ? "Kata sandi tidak sama" : null}>
        <Input id="pw-confirm" type="password" autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} />
      </Field>
      <ErrorNotice error={change.error} title="Kata sandi belum dapat diganti" />
      {saved ? (
        <Alert variant="success">
          <CheckCircle2Icon aria-hidden="true" />
          <AlertTitle>Kata sandi diperbarui</AlertTitle>
          <AlertDescription>Sesi Anda di perangkat lain telah diakhiri.</AlertDescription>
        </Alert>
      ) : null}
      <Button type="submit" variant="brand" disabled={!ready || change.pending}>
        {change.pending ? "Menyimpan..." : "Ganti kata sandi"}
      </Button>
    </form>
  );
}

export function AccountView() {
  const { principal } = useAuth();
  return (
    <div className="space-y-6">
      <PageHeader title="Akun" description="Identitas sesi dan pengaturan kata sandi Anda." />
      <SectionCard title="Profil">
        <KeyValueList
          items={[
            { label: "Nama", value: principal.name },
            { label: "Email", value: principal.email },
            { label: "Peran", value: labelOf(ROLE_LABELS, principal.role) },
            { label: "ID faskes", value: <span className="font-mono text-xs">{principal.faskes_id}</span> },
          ]}
        />
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-muted-foreground">Izin yang diberikan peran ini ({principal.permissions.length})</summary>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {principal.permissions.map((permission) => (
              <li key={permission} className="rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-xs">
                {permission}
              </li>
            ))}
          </ul>
        </details>
      </SectionCard>
      <SectionCard title="Ganti kata sandi" description="Setelah diganti, sesi lain milik akun ini diakhiri.">
        <ChangePasswordForm />
      </SectionCard>
    </div>
  );
}

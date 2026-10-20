"use client";

import { FlaskConicalIcon, PlusIcon } from "lucide-react";
import { useState } from "react";

import { Field } from "@/components/shared/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { PolicyVersion } from "@/lib/api-types";

import { ConfirmDialog } from "../shared/confirm-dialog";
import { TierBadge } from "../shared/tier-badge";

const SAMPLE_FACTS = {
  vector_code: "phantom_billing",
  check_type: "evidence_presence",
  rule_validation: "simulasi",
  delta_present: true,
  coverage_adequate: true,
  unresolved_conflict: false,
  has_contradiction: false,
  only_out_of_window_matches: false,
  missing_ratio: 1,
  citation_valid_count: 1,
  citation_invalid_count: 0,
};

function parseJson(text: string): { value: unknown; error: string | null } {
  try {
    return { value: JSON.parse(text), error: null };
  } catch {
    return { value: null, error: "JSON tidak valid" };
  }
}

export function PreviewPolicyDialog({ policy }: { policy: PolicyVersion }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(JSON.stringify(SAMPLE_FACTS, null, 2));
  const [result, setResult] = useState<{ tier: string; rule: string; priority: number } | null>(null);
  const parsed = parseJson(text);
  const run = useAction(() =>
    apiFetch<{ tier: string; rule: string; priority: number }>(`/v1/policy-versions/${policy.id}/preview`, {
      method: "POST",
      json: { facts: parsed.value },
    }),
  );
  const valid = parsed.error === null && parsed.value !== null && typeof parsed.value === "object" && !Array.isArray(parsed.value);

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          run.reset();
          setResult(null);
          setOpen(true);
        }}
      >
        <FlaskConicalIcon aria-hidden="true" />
        Uji kebijakan
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        wide
        title={`Uji kebijakan ${policy.version}`}
        description="Simulasi deterministik: fakta yang Anda isi dievaluasi oleh aturan kebijakan menurut prioritas. Tidak ada data klaim yang diubah."
        confirmLabel="Jalankan simulasi"
        pending={run.pending}
        error={run.error}
        disabled={!valid}
        onConfirm={async () => {
          const outcome = await run.run();
          if (outcome) setResult(outcome);
        }}
      >
        <Field id="pv-facts" label="Fakta (JSON)" error={parsed.error}>
          <Textarea id="pv-facts" rows={12} className="font-mono text-xs" value={text} onChange={(event) => setText(event.target.value)} />
        </Field>
        {result ? (
          <p className="flex flex-wrap items-center gap-2 rounded-2xl bg-lavender/50 p-3 text-sm">
            Hasil: <TierBadge tier={result.tier} /> oleh aturan <span className="font-mono text-xs">{result.rule}</span> (prioritas{" "}
            {result.priority}). Safety Governor masih dapat menurunkan tier saat pemeriksaan nyata.
          </p>
        ) : null}
      </ConfirmDialog>
    </>
  );
}

type RuleDraft = { code: string; tier: string; priority: number; condition: Record<string, unknown> };

export function CreatePolicyDialog({ template, onDone }: { template: PolicyVersion | null; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [version, setVersion] = useState("");
  const [text, setText] = useState("");
  const parsed = parseJson(text);
  const save = useAction(() =>
    apiFetch<PolicyVersion>("/v1/policy-versions", {
      method: "POST",
      json: { version: version.trim(), rules: parsed.value },
    }),
  );
  const valid = parsed.error === null && Array.isArray(parsed.value) && parsed.value.length > 0;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          save.reset();
          const drafts: RuleDraft[] = (template?.rules ?? []).map((rule) => ({
            code: rule.code,
            tier: rule.tier,
            priority: rule.priority,
            condition: rule.condition,
          }));
          setText(JSON.stringify(drafts, null, 2));
          setOpen(true);
        }}
      >
        <PlusIcon aria-hidden="true" />
        Versi kebijakan baru
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        wide
        title="Versi kebijakan baru"
        description="Dibuat sebagai draf dari aturan yang Anda ubah. Server menolak kebijakan tanpa aturan T0, tanpa aturan penampung, atau dengan T0 setelah aturan risiko."
        confirmLabel="Buat draf"
        pending={save.pending}
        error={save.error}
        disabled={!version.trim() || !valid}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            setVersion("");
            onDone();
          }
        }}
      >
        <div className="space-y-3">
          <Field id="np-version" label="Label versi" hint="Harus unik, mis. policy-sim-1.1.">
            <Input id="np-version" value={version} maxLength={64} onChange={(event) => setVersion(event.target.value)} />
          </Field>
          <Field id="np-rules" label="Aturan kebijakan (JSON)" hint="Larik {code, tier, priority, condition}. Dievaluasi urut prioritas; yang pertama cocok menang." error={parsed.error}>
            <Textarea id="np-rules" rows={14} className="font-mono text-xs" value={text} onChange={(event) => setText(event.target.value)} />
          </Field>
        </div>
      </ConfirmDialog>
    </>
  );
}

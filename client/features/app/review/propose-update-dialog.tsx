"use client";

import { useRouter } from "next/navigation";
import { GitPullRequestArrowIcon } from "lucide-react";
import { useState } from "react";

import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import type { RuleUpdate, RuleVersion } from "@/lib/api-types";

import { ConfirmDialog } from "../shared/confirm-dialog";

type ProposeUpdateDialogProps = {
  verdictId: string;
  ruleVersionId: string;
};

type SpecPatch = Record<string, unknown>;

function diffSpec(original: Record<string, unknown>, edited: Record<string, unknown>): SpecPatch {
  const patch: SpecPatch = {};
  for (const key of Object.keys(edited)) {
    if (JSON.stringify(edited[key]) !== JSON.stringify(original[key])) patch[key] = edited[key];
  }
  for (const key of Object.keys(original)) {
    if (!(key in edited)) patch[key] = null;
  }
  return patch;
}

function parseSpec(text: string): { value: Record<string, unknown> | null; error: string | null } {
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { value: null, error: "Spesifikasi harus berupa objek JSON" };
    }
    return { value: parsed as Record<string, unknown>, error: null };
  } catch {
    return { value: null, error: "JSON tidak valid" };
  }
}

export function ProposeUpdateDialog({ verdictId, ruleVersionId }: ProposeUpdateDialogProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [ruleId, setRuleId] = useState("");
  const [specText, setSpecText] = useState("");
  const [rationale, setRationale] = useState("");
  const version = useApi<RuleVersion>(open ? `/v1/rule-versions/${ruleVersionId}` : null);

  const rules = version.data?.expected_rules ?? [];
  const selected = rules.find((rule) => rule.id === ruleId) ?? null;
  const parsed = specText ? parseSpec(specText) : { value: null, error: null };
  const patch = selected && parsed.value ? diffSpec(selected.spec, parsed.value) : null;
  const changed = patch !== null && Object.keys(patch).length > 0;

  const propose = useAction(() =>
    apiFetch<RuleUpdate>("/v1/rule-updates", {
      method: "POST",
      json: {
        basis_verdict_ids: [verdictId],
        base_rule_version_id: ruleVersionId,
        expected_rule_id: ruleId,
        spec_patch: patch,
        rationale: rationale.trim(),
      },
    }),
  );

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          propose.reset();
          setOpen(true);
        }}
      >
        <GitPullRequestArrowIcon aria-hidden="true" />
        Usulkan pembaruan aturan
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        wide
        title="Usulkan pembaruan aturan dari verdict ini"
        description="Usulan hanya berupa proposal. Aturan aktif tidak berubah sampai usulan dievaluasi pada set validasi, disetujui pihak lain, lalu diaktifkan sebagai versi baru."
        confirmLabel="Kirim usulan"
        pending={propose.pending}
        error={propose.error ?? version.error}
        disabled={!changed || rationale.trim().length < 10 || parsed.error !== null}
        onConfirm={async () => {
          const saved = await propose.run();
          if (saved) {
            setOpen(false);
            router.push("/usulan-aturan");
          }
        }}
      >
        <div className="space-y-3">
          <Field id="upd-rule" label="Expected rule yang diubah">
            <OptionSelect
              id="upd-rule"
              value={ruleId}
              placeholder={version.loading ? "Memuat aturan..." : "Pilih expected rule"}
              options={rules.map((rule) => ({ value: rule.id, label: `Pola kode ${rule.code_pattern}` }))}
              onChange={(value) => {
                setRuleId(value);
                const next = rules.find((rule) => rule.id === value);
                setSpecText(next ? JSON.stringify(next.spec, null, 2) : "");
              }}
            />
          </Field>
          {selected ? (
            <Field
              id="upd-spec"
              label="Spesifikasi setelah diubah (JSON)"
              hint="Ubah bagian yang perlu direvisi. Hanya bagian yang berbeda dari aturan saat ini yang dikirim."
              error={parsed.error}
            >
              <Textarea
                id="upd-spec"
                rows={12}
                className="font-mono text-xs"
                value={specText}
                onChange={(event) => setSpecText(event.target.value)}
              />
            </Field>
          ) : null}
          <Field id="upd-reason" label="Alasan usulan" hint="Minimal 10 karakter; jelaskan temuan yang dikoreksi verdict ini.">
            <Textarea id="upd-reason" rows={3} maxLength={1000} value={rationale} onChange={(event) => setRationale(event.target.value)} />
          </Field>
        </div>
      </ConfirmDialog>
    </>
  );
}

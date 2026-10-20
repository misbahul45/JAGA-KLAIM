"use client";

import { PlusIcon } from "lucide-react";
import { useState } from "react";

import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { RuleSet, RuleVersion } from "@/lib/api-types";

import { ConfirmDialog } from "../shared/confirm-dialog";

type ExpectedRuleDraft = { code_pattern: string; spec: Record<string, unknown> };

function parseRules(text: string): { value: ExpectedRuleDraft[]; error: string | null } {
  if (!text.trim()) return { value: [], error: null };
  try {
    const parsed: unknown = JSON.parse(text);
    if (!Array.isArray(parsed)) return { value: [], error: "Harus berupa larik JSON" };
    const rules = parsed.map((item) => {
      const record = item as { code_pattern?: unknown; spec?: unknown };
      if (typeof record.code_pattern !== "string" || typeof record.spec !== "object" || record.spec === null) {
        throw new Error("format");
      }
      return { code_pattern: record.code_pattern, spec: record.spec as Record<string, unknown> };
    });
    return { value: rules, error: null };
  } catch {
    return { value: [], error: "Setiap butir harus berisi code_pattern dan spec" };
  }
}

type CreateRuleVersionDialogProps = {
  ruleSet: RuleSet;
  onDone: () => void;
};

export function CreateRuleVersionDialog({ ruleSet, onDone }: CreateRuleVersionDialogProps) {
  const [open, setOpen] = useState(false);
  const [version, setVersion] = useState("");
  const [base, setBase] = useState(ruleSet.active_version_id ?? ruleSet.versions[0]?.id ?? "");
  const [validation, setValidation] = useState("belum_tervalidasi");
  const [rulesText, setRulesText] = useState("");
  const parsed = parseRules(rulesText);
  const save = useAction(() =>
    apiFetch<RuleVersion>("/v1/rule-versions", {
      method: "POST",
      json: {
        rule_set_id: ruleSet.id,
        version: version.trim(),
        validation_status: validation,
        base_version_id: rulesText.trim() ? null : base || null,
        expected_rules: parsed.value.map((rule) => ({ code_pattern: rule.code_pattern, spec: rule.spec })),
      },
    }),
  );

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          save.reset();
          setOpen(true);
        }}
      >
        <PlusIcon aria-hidden="true" />
        Versi baru
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        wide
        title={`Versi baru untuk ${ruleSet.name}`}
        description="Versi baru dibuat sebagai draf. Ia baru berlaku setelah diajukan, disetujui pihak lain, dan diaktifkan. Status tervalidasi pakar hanya dapat ditetapkan saat persetujuan."
        confirmLabel="Buat draf"
        pending={save.pending}
        error={save.error ?? undefined}
        disabled={!version.trim() || parsed.error !== null || (!rulesText.trim() && !base)}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            setVersion("");
            setRulesText("");
            onDone();
          }
        }}
      >
        <div className="space-y-3">
          <Field id="rv-label" label="Label versi" hint="Contoh: 1.1. Huruf, angka, titik, garis, plus.">
            <Input id="rv-label" value={version} maxLength={32} onChange={(event) => setVersion(event.target.value)} />
          </Field>
          <Field id="rv-validation" label="Status validasi awal">
            <OptionSelect
              id="rv-validation"
              value={validation}
              onChange={setValidation}
              options={[
                { value: "belum_tervalidasi", label: "Belum tervalidasi pakar" },
                { value: "simulasi", label: "Aturan simulasi" },
              ]}
            />
          </Field>
          <Field id="rv-base" label="Salin aturan dari versi" hint="Diabaikan bila Anda mengisi JSON aturan di bawah.">
            <OptionSelect
              id="rv-base"
              value={base}
              onChange={setBase}
              options={ruleSet.versions.map((item) => ({ value: item.id, label: `${item.version} (${item.status})` }))}
            />
          </Field>
          <Field
            id="rv-rules"
            label="Aturan baru (JSON, opsional)"
            hint='Larik objek {"code_pattern": "...", "spec": {...}}. Spesifikasi divalidasi server.'
            error={parsed.error}
          >
            <Textarea id="rv-rules" rows={6} className="font-mono text-xs" value={rulesText} onChange={(event) => setRulesText(event.target.value)} />
          </Field>
        </div>
      </ConfirmDialog>
    </>
  );
}

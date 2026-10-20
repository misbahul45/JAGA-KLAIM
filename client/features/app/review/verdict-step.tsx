"use client";

import { useState } from "react";

import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { VerdictRecord } from "@/lib/api-types";
import { formatDateTime, formatDuration, shortId } from "@/lib/format";

import { ConfirmDialog } from "../shared/confirm-dialog";
import { FOLLOW_UP_LABELS, VERDICT_LABELS, labelOf } from "../shared/labels";

const VERDICT_OPTIONS = Object.entries(VERDICT_LABELS).map(([value, label]) => ({ value, label }));
const FOLLOW_UP_OPTIONS = Object.entries(FOLLOW_UP_LABELS).map(([value, label]) => ({ value, label }));

export function currentVerdict(verdicts: VerdictRecord[]): VerdictRecord | null {
  const superseded = new Set(verdicts.map((item) => item.supersedes_verdict_id).filter((id) => id !== null));
  return verdicts.find((item) => !superseded.has(item.id)) ?? null;
}

type VerdictFormProps = {
  interventionId: string;
  correction: boolean;
  initial?: VerdictRecord | null;
  onSaved: () => void;
};

export function VerdictForm({ interventionId, correction, initial, onSaved }: VerdictFormProps) {
  const [verdict, setVerdict] = useState(initial?.verdict ?? "");
  const [followUp, setFollowUp] = useState(initial?.follow_up ?? "proceed");
  const [rationale, setRationale] = useState("");
  const [open, setOpen] = useState(false);
  const path = correction
    ? `/v1/interventions/${interventionId}/verdict/correction`
    : `/v1/interventions/${interventionId}/verdict`;
  const save = useAction(() =>
    apiFetch<VerdictRecord>(path, {
      method: "POST",
      json: { verdict, follow_up: followUp, rationale: rationale.trim() },
    }),
  );
  const ready = verdict !== "" && rationale.trim().length >= 10;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="verdict" label="Verdict Anda">
          <OptionSelect id="verdict" value={verdict} options={VERDICT_OPTIONS} placeholder="Pilih verdict" onChange={setVerdict} />
        </Field>
        <Field id="follow-up" label="Tindak lanjut">
          <OptionSelect id="follow-up" value={followUp} options={FOLLOW_UP_OPTIONS} onChange={setFollowUp} />
        </Field>
      </div>
      <Field id="rationale" label="Alasan" hint="Minimal 10 karakter. Alasan dicatat pada audit trail.">
        <Textarea id="rationale" rows={4} maxLength={2000} value={rationale} onChange={(event) => setRationale(event.target.value)} />
      </Field>
      <Button
        variant={correction ? "outline" : "brand"}
        disabled={!ready}
        onClick={() => {
          save.reset();
          setOpen(true);
        }}
      >
        {correction ? "Catat koreksi verdict" : "Catat verdict"}
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={correction ? "Catat koreksi verdict?" : "Catat verdict?"}
        description={
          correction
            ? "Verdict lama tidak dihapus. Koreksi dicatat sebagai catatan baru yang menggantikannya, lengkap dengan alasan."
            : "Verdict tersimpan pada audit trail. Perubahan di kemudian hari hanya dapat dilakukan lewat koreksi bercatatan."
        }
        confirmLabel={correction ? "Catat koreksi" : "Catat verdict"}
        pending={save.pending}
        error={save.error}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            setRationale("");
            onSaved();
          }
        }}
      />
    </div>
  );
}

export function VerdictHistory({ verdicts }: { verdicts: VerdictRecord[] }) {
  if (verdicts.length === 0) return null;
  const current = currentVerdict(verdicts);
  return (
    <ul className="space-y-3">
      {verdicts.map((item) => (
        <li key={item.id} className="rounded-2xl border border-line bg-surface p-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={item.id === current?.id ? "success" : "neutral"}>
              {item.id === current?.id ? "Verdict berlaku" : "Digantikan"}
            </Badge>
            <span className="font-medium text-ink">{labelOf(VERDICT_LABELS, item.verdict)}</span>
            <span className="text-muted-foreground">· {labelOf(FOLLOW_UP_LABELS, item.follow_up)}</span>
          </div>
          {item.rationale ? <p className="mt-2 whitespace-pre-wrap text-ink">{item.rationale}</p> : null}
          <p className="mt-2 text-xs text-muted-foreground">
            {formatDateTime(item.created_at)} · verifikator {shortId(item.verifier_id)}
            {item.supersedes_verdict_id ? ` · mengoreksi ${shortId(item.supersedes_verdict_id)}` : ""}
            {item.supersedes_verdict_id === null ? ` · waktu keputusan ${formatDuration(item.time_to_decision_ms)}` : ""}
          </p>
        </li>
      ))}
    </ul>
  );
}

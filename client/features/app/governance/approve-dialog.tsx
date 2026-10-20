"use client";

import { useState } from "react";

import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";

import { ConfirmDialog } from "../shared/confirm-dialog";
import { STATUS_TABLES } from "../shared/labels";

const KEEP = "keep";

type ApproveDialogProps = {
  path: string;
  title: string;
  description: string;
  disabled?: boolean;
  disabledReason?: string;
  onDone: () => void;
};

export function ApproveDialog({ path, title, description, disabled = false, disabledReason, onDone }: ApproveDialogProps) {
  const [open, setOpen] = useState(false);
  const [validation, setValidation] = useState(KEEP);
  const [confirmed, setConfirmed] = useState(false);
  const [note, setNote] = useState("");
  const expert = validation === "tervalidasi_pakar";
  const options = [
    { value: KEEP, label: "Pertahankan status validasi saat ini" },
    ...Object.entries(STATUS_TABLES.validation).map(([value, entry]) => ({ value, label: entry.label })),
  ];
  const action = useAction(() =>
    apiFetch<unknown>(path, {
      method: "POST",
      json: {
        validation_status: validation === KEEP ? null : validation,
        expert_validation_confirmed: expert && confirmed,
        note: note.trim() || null,
      },
    }),
  );

  return (
    <>
      <Button
        variant="brand"
        size="sm"
        disabled={disabled}
        title={disabled ? disabledReason : undefined}
        onClick={() => {
          action.reset();
          setOpen(true);
        }}
      >
        Setujui
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        wide
        title={title}
        description={description}
        confirmLabel="Setujui"
        pending={action.pending}
        error={action.error}
        disabled={expert && (!confirmed || note.trim().length < 10)}
        onConfirm={async () => {
          const result = await action.run();
          if (result !== undefined) {
            setOpen(false);
            onDone();
          }
        }}
      >
        <div className="space-y-3">
          <Field id="apv-validation" label="Status validasi aturan">
            <OptionSelect id="apv-validation" value={validation} options={options} onChange={setValidation} />
          </Field>
          {expert ? (
            <>
              <label className="flex items-start gap-2 rounded-2xl border border-line bg-surface p-3 text-sm">
                <Checkbox checked={confirmed} onCheckedChange={(checked) => setConfirmed(checked === true)} />
                <span>
                  Saya menyatakan aturan ini telah divalidasi oleh pakar casemix/RMIK yang berwenang. Pernyataan
                  ini tidak dapat dibuat atas nama pihak lain.
                </span>
              </label>
              <Field id="apv-note" label="Dasar validasi" hint="Minimal 10 karakter: siapa yang memvalidasi dan dasarnya.">
                <Textarea id="apv-note" rows={3} maxLength={1000} value={note} onChange={(event) => setNote(event.target.value)} />
              </Field>
            </>
          ) : (
            <Field id="apv-note2" label="Catatan (opsional)">
              <Textarea id="apv-note2" rows={2} maxLength={1000} value={note} onChange={(event) => setNote(event.target.value)} />
            </Field>
          )}
        </div>
      </ConfirmDialog>
    </>
  );
}

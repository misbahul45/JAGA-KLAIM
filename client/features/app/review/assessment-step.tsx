"use client";

import { useState } from "react";

import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { Assessment } from "@/lib/api-types";

import { ConfirmDialog } from "../shared/confirm-dialog";
import { VERDICT_LABELS } from "../shared/labels";

const OPTIONS = Object.entries(VERDICT_LABELS).map(([value, label]) => ({ value, label }));

type AssessmentStepProps = {
  interventionId: string;
  onSaved: () => void;
};

export function AssessmentStep({ interventionId, onSaved }: AssessmentStepProps) {
  const [verdict, setVerdict] = useState("");
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  const save = useAction(() =>
    apiFetch<Assessment>(`/v1/interventions/${interventionId}/assessment`, {
      method: "POST",
      json: { self_verdict: verdict, note: note.trim() || null },
    }),
  );

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Tinjau bukti di atas, lalu tulis penilaian Anda sendiri tentang apakah bukti mendukung kode klaim.
        Rekomendasi sistem baru terbuka setelah penilaian ini tersimpan, dan penilaian tidak dapat diubah.
      </p>
      <Field id="self-verdict" label="Penilaian mandiri Anda">
        <OptionSelect id="self-verdict" value={verdict} options={OPTIONS} placeholder="Pilih penilaian" onChange={setVerdict} />
      </Field>
      <Field id="self-note" label="Catatan (opsional)" hint="Maksimal 2.000 karakter.">
        <Textarea id="self-note" rows={3} maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} />
      </Field>
      <Button
        variant="brand"
        disabled={verdict === ""}
        onClick={() => {
          save.reset();
          setOpen(true);
        }}
      >
        Simpan penilaian mandiri
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Simpan penilaian mandiri?"
        description="Penilaian tersimpan permanen sebagai pembanding terhadap rekomendasi sistem dan tidak dapat diubah. Setelah itu rekomendasi sistem dibuka."
        confirmLabel="Simpan dan buka rekomendasi"
        pending={save.pending}
        error={save.error}
        onConfirm={async () => {
          const saved = await save.run();
          if (saved) {
            setOpen(false);
            onSaved();
          }
        }}
      />
    </div>
  );
}

"use client";

import { PlusIcon } from "lucide-react";
import { useState } from "react";

import { Field } from "@/components/shared/field";
import { OptionSelect } from "@/components/shared/option-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { useApi } from "@/hooks/use-api";
import { apiFetch } from "@/lib/api";
import type { Evidence, Source } from "@/lib/api-types";
import { toIsoFromLocal } from "@/lib/format";

import { ConfirmDialog } from "../shared/confirm-dialog";
import { EVIDENCE_KIND_LABELS } from "../shared/labels";

type IngestEvidenceDialogProps = {
  claimId: string;
  onDone: () => void;
};

const KIND_OPTIONS = Object.entries(EVIDENCE_KIND_LABELS).map(([value, label]) => ({ value, label }));
const ASSERTION_OPTIONS = [
  { value: "supports", label: "Mendukung kode klaim" },
  { value: "negates", label: "Menafikan kode klaim (mis. tindakan dibatalkan)" },
];

export function IngestEvidenceDialog({ claimId, onDone }: IngestEvidenceDialogProps) {
  const [open, setOpen] = useState(false);
  const [sourceId, setSourceId] = useState("");
  const [kind, setKind] = useState("catatan_tindakan");
  const [assertion, setAssertion] = useState("supports");
  const [recordedAt, setRecordedAt] = useState("");
  const [content, setContent] = useState("");
  const sources = useApi<Source[]>(open ? "/v1/evidence-sources" : null);

  const options = (sources.data ?? [])
    .filter((source) => source.is_enabled)
    .map((source) => ({ value: source.id, label: `${source.system_ref} (${source.source_type})` }));

  const ingest = useAction(() =>
    apiFetch<Evidence>(`/v1/claims/${claimId}/evidence`, {
      method: "POST",
      json: {
        source_id: sourceId,
        recorded_at: toIsoFromLocal(recordedAt),
        kind,
        assertion,
        content_text: content,
      },
    }),
  );

  const ready = sourceId !== "" && toIsoFromLocal(recordedAt) !== null && content.trim().length > 0;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          ingest.reset();
          setOpen(true);
        }}
      >
        <PlusIcon aria-hidden="true" />
        Tambah bukti
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        wide
        title="Tambah bukti dari sumber yang diizinkan"
        description="Teks bukti diperlakukan sebagai data, bukan instruksi. Teks yang menyerupai instruksi akan dikarantina dan tidak dipakai sebagai dasar temuan. Jangan memasukkan data pasien nyata pada prototipe ini."
        confirmLabel="Simpan bukti"
        pending={ingest.pending}
        error={ingest.error ?? sources.error}
        disabled={!ready}
        onConfirm={async () => {
          const saved = await ingest.run();
          if (saved) {
            setOpen(false);
            setContent("");
            onDone();
          }
        }}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="ev-source" label="Sumber bukti" className="sm:col-span-2">
            <OptionSelect
              id="ev-source"
              value={sourceId}
              options={options}
              placeholder={sources.loading ? "Memuat sumber..." : "Pilih sumber"}
              onChange={setSourceId}
            />
          </Field>
          <Field id="ev-kind" label="Jenis bukti">
            <OptionSelect id="ev-kind" value={kind} options={KIND_OPTIONS} onChange={setKind} />
          </Field>
          <Field id="ev-assertion" label="Sikap bukti">
            <OptionSelect id="ev-assertion" value={assertion} options={ASSERTION_OPTIONS} onChange={setAssertion} />
          </Field>
          <Field id="ev-time" label="Waktu pencatatan" className="sm:col-span-2">
            <Input id="ev-time" type="datetime-local" value={recordedAt} onChange={(event) => setRecordedAt(event.target.value)} />
          </Field>
          <Field id="ev-content" label="Isi bukti" hint="Maksimal 50.000 karakter." className="sm:col-span-2">
            <Textarea
              id="ev-content"
              rows={6}
              maxLength={50000}
              value={content}
              onChange={(event) => setContent(event.target.value)}
            />
          </Field>
        </div>
      </ConfirmDialog>
    </>
  );
}

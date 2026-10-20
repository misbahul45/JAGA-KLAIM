"use client";

import { useState, type FormEvent } from "react";

import { ErrorNotice } from "@/components/shared/error-notice";
import { Field } from "@/components/shared/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { Claim } from "@/lib/api-types";
import { toIsoFromLocal, toLocalInput } from "@/lib/format";

import { CodesEditor, draftsFrom, type CodeDraft } from "./codes-editor";

type ClaimFormProps = {
  claim?: Claim;
  onDone: (claim: Claim) => void;
  onCancel?: () => void;
};

const EMPTY_CODES: CodeDraft[] = [
  { key: "k0", code_type: "procedure", code: "", position: "", description: "" },
];

function codePayload(codes: CodeDraft[]) {
  return codes.map((code) => ({
    code_type: code.code_type,
    code: code.code.trim(),
    position: code.position.trim() || null,
    description: code.description.trim() || null,
  }));
}

export function ClaimForm({ claim, onDone, onCancel }: ClaimFormProps) {
  const [episodeNo, setEpisodeNo] = useState(claim?.episode_no ?? "");
  const [pseudonym, setPseudonym] = useState(claim?.patient_pseudonym ?? "");
  const [start, setStart] = useState(toLocalInput(claim?.episode_start));
  const [end, setEnd] = useState(toLocalInput(claim?.episode_end));
  const [codes, setCodes] = useState<CodeDraft[]>(claim ? draftsFrom(claim.codes) : EMPTY_CODES);

  const save = useAction(async () => {
    const period = { episode_start: toIsoFromLocal(start), episode_end: toIsoFromLocal(end) };
    if (claim) {
      return apiFetch<Claim>(`/v1/claims/${claim.id}`, {
        method: "PATCH",
        json: { expected_version: claim.version, codes: codePayload(codes), ...period },
      });
    }
    return apiFetch<Claim>("/v1/claims", {
      method: "POST",
      json: {
        episode_no: episodeNo.trim(),
        patient_pseudonym: pseudonym.trim(),
        codes: codePayload(codes),
        ...period,
      },
    });
  });

  const ready =
    codes.length > 0 &&
    codes.every((code) => code.code.trim().length > 0) &&
    (claim !== undefined || (episodeNo.trim().length >= 3 && pseudonym.trim().length >= 3));

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const saved = await save.run();
    if (saved) onDone(saved);
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {claim === undefined ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="episode" label="Nomor episode" hint="Huruf, angka, titik, garis, atau garis miring (3-64 karakter).">
            <Input id="episode" value={episodeNo} onChange={(event) => setEpisodeNo(event.target.value)} maxLength={64} />
          </Field>
          <Field
            id="pseudonym"
            label="Pseudonim pasien"
            hint="Gunakan pseudonim buram. Jangan memasukkan NIK atau nomor peserta."
          >
            <Input id="pseudonym" value={pseudonym} onChange={(event) => setPseudonym(event.target.value)} maxLength={64} />
          </Field>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="start" label="Awal episode (opsional)">
          <Input id="start" type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} />
        </Field>
        <Field
          id="end"
          label="Akhir episode (opsional)"
          hint="Dipakai untuk memeriksa apakah bukti berada dalam periode pelayanan."
        >
          <Input id="end" type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} />
        </Field>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium text-ink">Kode klaim (hasil coding dan grouping)</p>
        <CodesEditor codes={codes} onChange={setCodes} />
      </div>

      <ErrorNotice error={save.error} title="Klaim belum dapat disimpan" />

      <div className="flex flex-wrap justify-end gap-2">
        {onCancel ? (
          <Button variant="outline" onClick={onCancel} disabled={save.pending}>
            Batal
          </Button>
        ) : null}
        <Button type="submit" variant="brand" disabled={!ready || save.pending}>
          {save.pending ? "Menyimpan..." : claim ? "Simpan perubahan" : "Simpan sebagai draf"}
        </Button>
      </div>
    </form>
  );
}

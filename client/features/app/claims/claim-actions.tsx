"use client";

import { LockIcon, PencilIcon, RefreshCwIcon, SendIcon } from "lucide-react";
import { useState } from "react";

import { Field } from "@/components/shared/field";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";
import type { Claim, ClaimDetail, Job } from "@/lib/api-types";
import { newIdempotencyKey } from "@/lib/idempotency";

import { useAuth } from "../auth/auth-context";
import { ConfirmDialog } from "../shared/confirm-dialog";
import { ClaimForm } from "./claim-form";
import { IngestEvidenceDialog } from "./ingest-evidence-dialog";

const EDITABLE = ["draft", "returned_to_coder", "needs_clarification"];
const SUBMITTABLE = ["draft", "needs_clarification"];
const RERUNNABLE = ["coding_submitted", "under_review", "ready_to_lock"];

type ActionProps = {
  detail: ClaimDetail;
  onChanged: () => void;
};

function SubmitCodingAction({ detail, onChanged }: ActionProps) {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const action = useAction((idempotencyKey: string) =>
    apiFetch<Job>(`/v1/claims/${detail.id}/submit-coding`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  );
  return (
    <>
      <Button
        variant="brand"
        size="sm"
        onClick={() => {
          action.reset();
          setKey(newIdempotencyKey(`submit-${detail.id.slice(0, 8)}`));
          setOpen(true);
        }}
      >
        <SendIcon aria-hidden="true" />
        Kirim coding
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Kirim coding untuk diperiksa?"
        description="Sistem membandingkan expected evidence dengan bukti yang tersedia di sumber yang diizinkan. Hasilnya berupa ketidaksesuaian yang perlu diperiksa manusia. Klaim tidak ditolak dan kode tidak diubah otomatis."
        confirmLabel="Kirim coding"
        pending={action.pending}
        error={action.error}
        onConfirm={async () => {
          const job = await action.run(key);
          if (job) {
            setOpen(false);
            onChanged();
          }
        }}
      />
    </>
  );
}

function RerunAction({ detail, onChanged }: ActionProps) {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const [reason, setReason] = useState("");
  const action = useAction((idempotencyKey: string) =>
    apiFetch<Job>(`/v1/claims/${detail.id}/investigations`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      json: { reason: reason.trim() },
    }),
  );
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => {
          action.reset();
          setKey(newIdempotencyKey(`rerun-${detail.id.slice(0, 8)}`));
          setOpen(true);
        }}
      >
        <RefreshCwIcon aria-hidden="true" />
        Periksa ulang
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Periksa ulang klaim"
        description="Hasil sebelumnya ditandai tidak berlaku dan tinjauan terbukanya digantikan oleh hasil baru."
        confirmLabel="Jalankan pemeriksaan ulang"
        pending={action.pending}
        error={action.error}
        disabled={reason.trim().length < 5}
        onConfirm={async () => {
          const job = await action.run(key);
          if (job) {
            setOpen(false);
            setReason("");
            onChanged();
          }
        }}
      >
        <Field id="rerun-reason" label="Alasan pemeriksaan ulang" hint="Minimal 5 karakter. Alasan dicatat pada audit trail.">
          <Textarea id="rerun-reason" rows={3} maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} />
        </Field>
      </ConfirmDialog>
    </>
  );
}

function LockAction({ detail, onChanged }: ActionProps) {
  const [open, setOpen] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const partial = detail.runs.some((run) => !run.stale && run.status === "partial");
  const action = useAction(() =>
    apiFetch<Claim>(`/v1/claims/${detail.id}/lock`, {
      method: "POST",
      json: { acknowledge_limitations: acknowledged },
    }),
  );
  return (
    <>
      <Button
        variant="default"
        size="sm"
        onClick={() => {
          action.reset();
          setAcknowledged(false);
          setOpen(true);
        }}
      >
        <LockIcon aria-hidden="true" />
        Kunci klaim
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Kunci klaim untuk diajukan?"
        description="Klaim yang dikunci tidak dapat diubah lagi. Pengajuan ke BPJS Kesehatan dilakukan faskes di luar sistem ini."
        confirmLabel="Kunci klaim"
        pending={action.pending}
        error={action.error}
        disabled={partial && !acknowledged}
        onConfirm={async () => {
          const locked = await action.run();
          if (locked) {
            setOpen(false);
            onChanged();
          }
        }}
      >
        {partial ? (
          <label className="flex items-start gap-2 rounded-2xl border border-line bg-surface p-3 text-sm">
            <Checkbox checked={acknowledged} onCheckedChange={(checked) => setAcknowledged(checked === true)} />
            <span>
              Sebagian pemeriksaan abstain atau tidak lengkap karena bukti belum memadai. Saya telah
              meninjau keterbatasan ini dan memahami bahwa bukti tidak ditemukan tidak membuktikan
              pelayanan tidak terjadi.
            </span>
          </label>
        ) : null}
      </ConfirmDialog>
    </>
  );
}

function EditAction({ detail, onChanged }: ActionProps) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <PencilIcon aria-hidden="true" />
        Ubah klaim
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full overflow-y-auto p-5 sm:max-w-2xl">
          <SheetHeader className="p-0">
            <SheetTitle>Ubah klaim {detail.episode_no}</SheetTitle>
            <SheetDescription>
              Mengubah kode atau periode menaikkan versi klaim dan menandai hasil pemeriksaan sebelumnya
              tidak berlaku. Klaim kembali menjadi draf.
            </SheetDescription>
          </SheetHeader>
          <ClaimForm
            claim={detail}
            onCancel={() => setOpen(false)}
            onDone={() => {
              setOpen(false);
              onChanged();
            }}
          />
        </SheetContent>
      </Sheet>
    </>
  );
}

export function ClaimActions({ detail, onChanged }: ActionProps) {
  const { can } = useAuth();
  return (
    <>
      {can("claim:write") && EDITABLE.includes(detail.status) ? (
        <EditAction detail={detail} onChanged={onChanged} />
      ) : null}
      {can("evidence:ingest") && detail.status !== "locked" ? (
        <IngestEvidenceDialog claimId={detail.id} onDone={onChanged} />
      ) : null}
      {can("claim:submit") && SUBMITTABLE.includes(detail.status) ? (
        <SubmitCodingAction detail={detail} onChanged={onChanged} />
      ) : null}
      {can("investigation:trigger") && RERUNNABLE.includes(detail.status) ? (
        <RerunAction detail={detail} onChanged={onChanged} />
      ) : null}
      {can("claim:lock") && detail.status === "ready_to_lock" ? (
        <LockAction detail={detail} onChanged={onChanged} />
      ) : null}
    </>
  );
}

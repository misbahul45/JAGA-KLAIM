"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeftIcon, InfoIcon, ShieldAlertIcon, TriangleAlertIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { ClaimDetail, Evidence } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { CODE_TYPE_LABELS, EVENT_LABELS, labelOf } from "../shared/labels";
import { EvidenceList } from "../shared/evidence-list";
import { KeyValueList } from "../shared/key-value";
import { QueryBoundary } from "../shared/query-boundary";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { usePolling } from "../shared/use-polling";
import { ClaimActions } from "./claim-actions";
import { ClaimRuns } from "./claim-runs";

function Banners({ detail }: { detail: ClaimDetail }) {
  const { can } = useAuth();
  const job = detail.latest_job;
  const working = job?.status === "queued" || job?.status === "processing";
  return (
    <div className="space-y-3">
      {working ? (
        <Alert variant="info">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>Pemeriksaan sedang berjalan</AlertTitle>
          <AlertDescription>
            {labelOf(EVENT_LABELS, job?.event_type)} berstatus <StatusBadge kind="job" value={job?.status} />. Halaman
            diperbarui otomatis.
          </AlertDescription>
        </Alert>
      ) : null}
      {job?.status === "failed" ? (
        <Alert variant="destructive">
          <TriangleAlertIcon aria-hidden="true" />
          <AlertTitle>Pemeriksaan gagal</AlertTitle>
          <AlertDescription>
            {job.error_message ?? "Pemeriksaan tidak dapat diselesaikan."} Hasil gagal tidak berarti klaim
            sesuai atau tidak sesuai. Minta pemeriksaan ulang.
          </AlertDescription>
        </Alert>
      ) : null}
      {detail.evidence_updated_after_run ? (
        <Alert variant="warning">
          <TriangleAlertIcon aria-hidden="true" />
          <AlertTitle>Bukti diperbarui setelah pemeriksaan terakhir</AlertTitle>
          <AlertDescription>
            Hasil yang tampil dapat sudah usang. Jalankan pemeriksaan ulang sebelum mengunci klaim.
          </AlertDescription>
        </Alert>
      ) : null}
      {detail.quarantined_count > 0 ? (
        <Alert variant="warning">
          <ShieldAlertIcon aria-hidden="true" />
          <AlertTitle>{detail.quarantined_count} bukti dikarantina</AlertTitle>
          <AlertDescription>
            Teks bukti tersebut menyerupai instruksi kepada sistem. Isinya tidak dipakai sebagai dasar
            temuan sampai ditinjau manusia.
          </AlertDescription>
        </Alert>
      ) : null}
      {detail.open_review_count > 0 && can("review:read") ? (
        <Alert variant="info">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>{detail.open_review_count} butir menunggu verifikasi manusia</AlertTitle>
          <AlertDescription>
            Buka hasil pemeriksaan di bawah atau{" "}
            <Link href="/tinjauan" className="underline underline-offset-3">
              antrean tinjauan
            </Link>
            .
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

function Body({ detail, evidence }: { detail: ClaimDetail; evidence: Evidence[] | null }) {
  return (
    <div className="space-y-6">
      <Banners detail={detail} />

      <SectionCard title="Ringkasan">
        <KeyValueList
          columns={3}
          items={[
            { label: "Status", value: <StatusBadge kind="claim" value={detail.status} /> },
            { label: "Versi klaim", value: `v${detail.version}` },
            { label: "Pseudonim pasien", value: <span className="font-mono text-xs">{detail.patient_pseudonym}</span> },
            { label: "Awal episode", value: formatDateTime(detail.episode_start) },
            { label: "Akhir episode", value: formatDateTime(detail.episode_end) },
            { label: "Coding dikirim", value: formatDateTime(detail.submitted_at) },
          ]}
        />
      </SectionCard>

      <SectionCard title="Kode klaim" description="Hasil coding dan grouping yang diperiksa.">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Jenis</TableHead>
                <TableHead>Kode</TableHead>
                <TableHead>Posisi</TableHead>
                <TableHead>Deskripsi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {detail.codes.map((code) => (
                <TableRow key={code.id}>
                  <TableCell>{labelOf(CODE_TYPE_LABELS, code.code_type)}</TableCell>
                  <TableCell className="font-mono text-xs font-medium">{code.code}</TableCell>
                  <TableCell>{code.position ?? "-"}</TableCell>
                  <TableCell className="whitespace-normal">{code.description ?? "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </SectionCard>

      <SectionCard
        title="Hasil pemeriksaan"
        description="Satu hasil per vektor risiko. Tier ditetapkan oleh policy engine berversi, bukan oleh model."
      >
        <ClaimRuns runs={detail.runs} />
      </SectionCard>

      <SectionCard
        title={`Bukti (${detail.evidence_count})`}
        description="Bukti yang tersedia dari sumber yang diizinkan faskes."
      >
        {evidence === null ? (
          <p className="text-sm text-muted-foreground">Peran Anda tidak dapat melihat daftar bukti.</p>
        ) : (
          <EvidenceList items={evidence} />
        )}
      </SectionCard>

      <div className="sr-only" aria-live="polite">
        {detail.latest_job ? `Status job terakhir: ${detail.latest_job.status}` : ""}
      </div>
    </div>
  );
}

export function ClaimDetailView() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const claim = useApi<ClaimDetail>(`/v1/claims/${id}`);
  const evidence = useApi<Evidence[]>(can("evidence:read") ? `/v1/claims/${id}/evidence` : null);

  const reloadClaim = claim.reload;
  const reloadEvidence = evidence.reload;
  const changed = () => {
    reloadClaim();
    reloadEvidence();
  };
  const working = claim.data?.latest_job?.status === "queued" || claim.data?.latest_job?.status === "processing";
  usePolling(working, changed);

  return (
    <div className="space-y-6">
      <PageHeader
        title={claim.data ? `Klaim ${claim.data.episode_no}` : "Klaim"}
        description="Detail klaim, hasil pemeriksaan, dan bukti yang tersedia."
        actions={
          <>
            <Link href="/klaim" className={buttonVariants({ variant: "outline", size: "sm" })}>
              <ArrowLeftIcon aria-hidden="true" />
              Daftar klaim
            </Link>
            {claim.data ? <ClaimActions detail={claim.data} onChanged={changed} /> : null}
          </>
        }
      />
      <QueryBoundary state={claim} rows={6}>
        {(detail) => <Body detail={detail} evidence={evidence.data} />}
      </QueryBoundary>
    </div>
  );
}

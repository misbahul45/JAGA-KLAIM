"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeftIcon, LockIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { RunDetail, RunFinding } from "@/lib/api-types";
import { formatDateTime, shortId } from "@/lib/format";

import { RequirePermission } from "../shared/require-permission";
import { STEP_LABELS, VECTOR_LABELS, labelOf } from "../shared/labels";
import { KeyValueList } from "../shared/key-value";
import { QueryBoundary } from "../shared/query-boundary";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";

function FindingRow({ finding }: { finding: RunFinding }) {
  return (
    <li className="rounded-2xl border border-line bg-surface p-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <TierBadge tier={finding.tier} />
        {finding.claim_code ? (
          <span className="rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-xs">{finding.claim_code}</span>
        ) : null}
        <Badge variant={finding.status === "valid" ? "success" : "warning"}>
          Temuan {finding.status === "valid" ? "valid" : "diturunkan"}
        </Badge>
      </div>
      {finding.revealed ? (
        <p className="mt-2 text-ink">{finding.mismatch_desc}</p>
      ) : (
        <p className="mt-2 flex items-start gap-2 text-muted-foreground">
          <LockIcon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          Isi temuan terkunci sampai Anda menyimpan penilaian mandiri pada workbench.
        </p>
      )}
      {finding.intervention_id ? (
        <Link
          href={`/tinjauan/${finding.intervention_id}`}
          className={`${buttonVariants({ variant: "outline", size: "sm" })} mt-3`}
        >
          Buka di workbench
        </Link>
      ) : null}
    </li>
  );
}

function Body({ run }: { run: RunDetail }) {
  const sources = (run.coverage.sources ?? []) as Record<string, unknown>[];
  const comparisons = run.coverage.comparisons ?? [];
  return (
    <div className="space-y-6">
      {run.stale ? (
        <Alert variant="warning">
          <AlertTitle>Hasil ini sudah tidak berlaku</AlertTitle>
          <AlertDescription>
            Klaim berubah atau diperiksa ulang setelah hasil ini dibuat. Hasil terbaru ada pada halaman klaim.
          </AlertDescription>
        </Alert>
      ) : null}
      {run.abstain_reason ? (
        <Alert variant="info">
          <AlertTitle>Abstain: bukti belum memadai</AlertTitle>
          <AlertDescription>
            {run.abstain_reason}. Abstain adalah gerbang kecukupan bukti, bukan penilaian bahwa klaim salah.
          </AlertDescription>
        </Alert>
      ) : null}

      <SectionCard title="Ringkasan pemeriksaan">
        <KeyValueList
          columns={3}
          items={[
            { label: "Vektor risiko", value: labelOf(VECTOR_LABELS, run.vector_code) },
            { label: "Status", value: <StatusBadge kind="run" value={run.status} /> },
            { label: "Hasil", value: <StatusBadge kind="outcome" value={run.outcome} /> },
            { label: "Versi klaim", value: `v${run.claim_version}` },
            { label: "Versi aturan", value: run.rule_version },
            { label: "Versi kebijakan", value: run.policy_version },
            { label: "Mesin pemeriksaan", value: `${run.model_name} ${run.model_version}` },
            { label: "Versi prompt", value: run.prompt_version },
            { label: "Pemicu", value: run.trigger },
            { label: "Dimulai", value: formatDateTime(run.started_at) },
            { label: "Selesai", value: formatDateTime(run.finished_at) },
            { label: "ID korelasi", value: <span className="font-mono text-xs">{run.correlation_id}</span> },
            {
              label: "Pemeriksaan ulang dari",
              value: run.rerun_of_run_id ? (
                <Link href={`/pemeriksaan/${run.rerun_of_run_id}`} className="font-mono text-xs text-brand underline-offset-4 hover:underline">
                  {shortId(run.rerun_of_run_id)}
                </Link>
              ) : (
                "-"
              ),
            },
          ]}
        />
        {run.validation_errors ? (
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-surface p-3 text-xs">
            {JSON.stringify(run.validation_errors, null, 2)}
          </pre>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Temuan"
        description="Tier ditetapkan policy engine berversi. Tidak ada temuan yang menolak atau mengubah klaim."
      >
        {run.findings.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Tidak ada temuan. Bila hasilnya No Action, tidak ada selisih antara expected dan observed evidence dan
            pemeriksaan tetap tercatat pada audit trail.
          </p>
        ) : (
          <ul className="space-y-3">
            {run.findings.map((finding) => (
              <FindingRow key={finding.id} finding={finding} />
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Cakupan sumber bukti" description="Kondisi sumber saat pemeriksaan dijalankan.">
        {sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">Tidak ada sumber bukti terdaftar saat pemeriksaan.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sumber</TableHead>
                  <TableHead>Tipe</TableHead>
                  <TableHead>Aktif</TableHead>
                  <TableHead>Kesehatan</TableHead>
                  <TableHead>Sinkronisasi terakhir</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sources.map((source) => (
                  <TableRow key={String(source.source_id)}>
                    <TableCell className="font-medium">{String(source.system_ref)}</TableCell>
                    <TableCell>{String(source.source_type)}</TableCell>
                    <TableCell>{source.enabled ? "Ya" : "Tidak"}</TableCell>
                    <TableCell>
                      <StatusBadge kind="health" value={String(source.health_status)} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTime(typeof source.last_synced_at === "string" ? source.last_synced_at : null)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {comparisons.length > 0 ? (
          <ul className="mt-4 space-y-2 text-sm">
            {comparisons.map((item) => (
              <li key={item.code} className="rounded-2xl bg-surface p-3">
                <span className="font-mono text-xs font-medium">{item.code}</span>
                <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                  {item.gaps.map((gap) => (
                    <li key={gap}>{gap}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Jejak langkah agent"
        description="Hanya langkah operasional dan nama tool dari allowlist. Teks klinis dan penalaran privat tidak disimpan."
      >
        <ol className="space-y-2">
          {run.steps.map((step) => (
            <li key={step.seq} className="rounded-2xl border border-line p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-muted-foreground">#{step.seq}</span>
                <span className="font-medium text-ink">{labelOf(STEP_LABELS, step.step_type)}</span>
                <Badge variant={step.status === "ok" ? "success" : "danger"}>{step.status}</Badge>
                {step.tool_name ? <span className="font-mono text-xs text-muted-foreground">{step.tool_name}</span> : null}
                {step.latency_ms !== null ? (
                  <span className="text-xs text-muted-foreground">{step.latency_ms} ms</span>
                ) : null}
              </div>
              {step.error_message ? <p className="mt-1 text-xs text-destructive">{step.error_message}</p> : null}
              {step.result_ref ? (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-muted-foreground">Ringkasan hasil</summary>
                  <pre className="mt-1 overflow-x-auto rounded-xl bg-surface p-2 text-xs">
                    {JSON.stringify(step.result_ref, null, 2)}
                  </pre>
                </details>
              ) : null}
            </li>
          ))}
        </ol>
      </SectionCard>
    </div>
  );
}

export function RunDetailView() {
  const { id } = useParams<{ id: string }>();
  const state = useApi<RunDetail>(`/v1/investigations/${id}`);
  return (
    <RequirePermission permission="investigation:read">
      <div className="space-y-6">
        <PageHeader
          title="Rincian pemeriksaan"
          description="Versi aturan dan kebijakan, cakupan sumber, jejak langkah, dan temuan untuk satu vektor risiko."
          actions={
            state.data ? (
              <Link href={`/klaim/${state.data.claim_id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                <ArrowLeftIcon aria-hidden="true" />
                Kembali ke klaim
              </Link>
            ) : null
          }
        />
        <QueryBoundary state={state} rows={6}>
          {(run) => <Body run={run} />}
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

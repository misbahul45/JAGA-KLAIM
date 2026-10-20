"use client";

import Link from "next/link";
import { GitPullRequestArrowIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { EvaluationSummary, RuleUpdate } from "@/lib/api-types";
import { formatDateTime, formatPercent, shortId } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { KeyValueList } from "../shared/key-value";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { ActionButton } from "./action-button";
import { ApproveDialog } from "./approve-dialog";

const METRIC_LABELS: Record<string, string> = {
  accuracy: "Kesesuaian dengan label",
  flag_precision: "Presisi flag",
  flag_recall: "Recall flag",
  abstention_rate: "Tingkat abstain",
  citation_fidelity: "Citation fidelity",
};

function EvaluationBlock({ update }: { update: RuleUpdate }) {
  const evaluation = update.evaluation;
  if (!evaluation) return <p className="text-sm text-muted-foreground">Belum dievaluasi.</p>;
  const baseline: EvaluationSummary = evaluation.baseline ?? {};
  const candidate: EvaluationSummary = evaluation.candidate ?? {};
  const regressions = evaluation.regression_count ?? 0;
  return (
    <div className="space-y-3">
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant={regressions === 0 ? "success" : "danger"}>{regressions} regresi</Badge>
        <Badge variant="info">{evaluation.improvement_count ?? 0} perbaikan</Badge>
        {evaluation.vector ? <span className="text-xs text-muted-foreground">vektor {evaluation.vector}</span> : null}
      </p>
      <div className="overflow-x-auto rounded-2xl border border-line">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ukuran</TableHead>
              <TableHead className="text-right">Aturan dasar</TableHead>
              <TableHead className="text-right">Usulan</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Object.entries(METRIC_LABELS).map(([key, label]) => (
              <TableRow key={key}>
                <TableCell>{label}</TableCell>
                <TableCell className="text-right tabular-nums">{formatPercent(baseline.overall?.[key])}</TableCell>
                <TableCell className="text-right tabular-nums">{formatPercent(candidate.overall?.[key])}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {(evaluation.changed_cases ?? []).length > 0 ? (
        <ul className="space-y-1 text-xs text-muted-foreground">
          {(evaluation.changed_cases ?? []).map((item) => (
            <li key={item.id}>
              Kasus <span className="font-mono">{item.id}</span>: {item.from} → {item.to} (label: {item.expected})
            </li>
          ))}
        </ul>
      ) : null}
      {candidate.validation_set ? <p className="text-xs text-muted-foreground">{candidate.validation_set}</p> : null}
    </div>
  );
}

function UpdateActions({ update, reload }: { update: RuleUpdate; reload: () => void }) {
  const { can, principal } = useAuth();
  const base = `/v1/rule-updates/${update.id}`;
  const proposer = update.proposed_by === principal.user_id;
  const regressed = (update.evaluation?.regression_count ?? 0) > 0;
  const canDecide = can("rule:approve");
  return (
    <>
      {can("rule:write") && update.status === "proposed" ? (
        <ActionButton
          label="Evaluasi offline"
          variant="brand"
          title="Jalankan evaluasi offline?"
          description="Sistem membuat versi kandidat dan membandingkannya dengan aturan dasar pada set validasi sintetis, tanpa menyentuh aturan aktif."
          path={`${base}/evaluate`}
          onDone={reload}
        />
      ) : null}
      {canDecide && update.status === "evaluated" ? (
        <ApproveDialog
          path={`${base}/approve`}
          title="Setujui usulan pembaruan"
          description="Persetujuan membuat versi kandidat berstatus disetujui, belum aktif. Pengusul tidak dapat menyetujui usulannya sendiri."
          disabled={proposer || regressed}
          disabledReason={proposer ? "Pengusul tidak boleh menyetujui usulannya sendiri" : "Evaluasi menemukan regresi"}
          onDone={reload}
        />
      ) : null}
      {canDecide && ["proposed", "evaluating", "evaluated"].includes(update.status) ? (
        <ActionButton
          label="Tolak"
          variant="destructive"
          tone="destructive"
          withReason
          disabled={proposer}
          title="Tolak usulan pembaruan?"
          description="Versi kandidat yang belum diaktifkan ikut ditolak."
          path={`${base}/reject`}
          onDone={reload}
        />
      ) : null}
      {canDecide && update.status === "approved" ? (
        <ActionButton
          label="Aktifkan"
          variant="brand"
          title="Aktifkan versi hasil usulan?"
          description="Versi aktif sebelumnya pada rule set dipensiunkan. Pemeriksaan berikutnya memakai versi baru; hasil lama tetap tercatat dengan versi yang dipakainya."
          path={`${base}/activate`}
          onDone={reload}
        />
      ) : null}
      {canDecide && update.status === "activated" ? (
        <ActionButton
          label="Rollback"
          variant="destructive"
          tone="destructive"
          title="Rollback ke aturan sebelumnya?"
          description="Versi hasil usulan dipensiunkan dan aturan dasar dipulihkan sebagai versi baru yang aktif."
          path={`${base}/rollback`}
          onDone={reload}
        />
      ) : null}
    </>
  );
}

function UpdateCard({ update, reload }: { update: RuleUpdate; reload: () => void }) {
  const rationale = typeof update.proposed_change.rationale === "string" ? update.proposed_change.rationale : null;
  return (
    <SectionCard
      title={`Usulan ${shortId(update.id)}`}
      description={rationale ?? undefined}
      actions={<UpdateActions update={update} reload={reload} />}
    >
      <KeyValueList
        columns={3}
        className="mb-4"
        items={[
          { label: "Status", value: <StatusBadge kind="update" value={update.status} /> },
          {
            label: "Dasar verdict manusia",
            value: (
              <span className="font-mono text-xs">
                {update.basis_verdict_ids.map((id) => shortId(id)).join(", ")} ({update.basis_verdict_ids.length})
              </span>
            ),
          },
          {
            label: "Versi aturan dasar",
            value: (
              <Link href={`/aturan/${update.base_rule_version_id}`} className="font-mono text-xs text-brand underline-offset-4 hover:underline">
                {shortId(update.base_rule_version_id)}
              </Link>
            ),
          },
          {
            label: "Versi hasil usulan",
            value: update.result_rule_version_id ? (
              <Link href={`/aturan/${update.result_rule_version_id}`} className="font-mono text-xs text-brand underline-offset-4 hover:underline">
                {shortId(update.result_rule_version_id)}
              </Link>
            ) : (
              "-"
            ),
          },
          { label: "Diusulkan oleh", value: update.proposed_by ? <span className="font-mono text-xs">{shortId(update.proposed_by)}</span> : "-" },
          { label: "Diputuskan oleh", value: update.decided_by ? <span className="font-mono text-xs">{shortId(update.decided_by)}</span> : "-" },
          { label: "Dibuat", value: formatDateTime(update.created_at) },
          { label: "Dievaluasi", value: formatDateTime(update.evaluated_at) },
          { label: "Diputuskan", value: formatDateTime(update.decided_at) },
        ]}
      />
      <details className="mb-4 text-sm">
        <summary className="cursor-pointer text-muted-foreground">Perubahan yang diusulkan</summary>
        <pre className="mt-2 overflow-x-auto rounded-xl bg-surface p-3 text-xs">{JSON.stringify(update.proposed_change, null, 2)}</pre>
      </details>
      <EvaluationBlock update={update} />
    </SectionCard>
  );
}

export function RuleUpdatesView() {
  const updates = useApi<RuleUpdate[]>("/v1/rule-updates");
  return (
    <RequirePermission permission="rule:read">
      <div className="space-y-6">
        <PageHeader
          title="Usulan pembaruan aturan"
          description="Verdict manusia dapat menjadi dasar usulan, tetapi tidak pernah mengubah aturan aktif secara langsung. Setiap usulan dievaluasi, disetujui pihak lain, lalu diaktifkan sebagai versi baru yang dapat di-rollback."
        />
        <Alert variant="warning">
          <AlertTitle>Set validasi sintetis</AlertTitle>
          <AlertDescription>
            Evaluasi offline memakai kasus sintetis buatan pengembang, bukan anotasi pakar casemix/RMIK. Hasilnya menguji
            konsistensi mesin dan mencegah regresi, bukan membuktikan kebenaran klinis.
          </AlertDescription>
        </Alert>
        <QueryBoundary state={updates} rows={5}>
          {(items) =>
            items.length === 0 ? (
              <EmptyState
                icon={GitPullRequestArrowIcon}
                title="Belum ada usulan pembaruan"
                description="Usulan dibuat verifikator dari workbench setelah verdict yang menyatakan temuan tidak didukung atau bukti tidak cukup."
              />
            ) : (
              <div className="space-y-6">
                {items.map((update) => (
                  <UpdateCard key={update.id} update={update} reload={updates.reload} />
                ))}
              </div>
            )
          }
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

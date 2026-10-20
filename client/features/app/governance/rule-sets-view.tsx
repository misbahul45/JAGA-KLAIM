"use client";

import Link from "next/link";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { RuleSet } from "@/lib/api-types";
import { formatDateTime, shortId } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { VECTOR_LABELS, labelOf } from "../shared/labels";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { CreateRuleVersionDialog } from "./create-rule-version-dialog";

function RuleSetCard({ ruleSet, reload }: { ruleSet: RuleSet; reload: () => void }) {
  const { can } = useAuth();
  const active = ruleSet.versions.find((version) => version.id === ruleSet.active_version_id) ?? null;
  return (
    <SectionCard
      title={`${labelOf(VECTOR_LABELS, ruleSet.vector.code)} · ${ruleSet.name}`}
      description={ruleSet.description ?? ruleSet.vector.description ?? undefined}
      actions={can("rule:write") ? <CreateRuleVersionDialog ruleSet={ruleSet} onDone={reload} /> : null}
    >
      <p className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Versi aktif:</span>
        {active ? (
          <>
            <span className="font-medium text-ink">{active.version}</span>
            <StatusBadge kind="validation" value={active.validation_status} />
          </>
        ) : (
          <span className="text-destructive">Belum ada versi aktif; pemeriksaan vektor ini tidak dapat berjalan.</span>
        )}
      </p>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Versi</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Validasi</TableHead>
              <TableHead>Disusun oleh</TableHead>
              <TableHead>Disetujui oleh</TableHead>
              <TableHead>Diaktifkan</TableHead>
              <TableHead className="text-right">Rincian</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ruleSet.versions.map((version) => (
              <TableRow key={version.id}>
                <TableCell className="font-medium">{version.version}</TableCell>
                <TableCell>
                  <StatusBadge kind="version" value={version.status} />
                </TableCell>
                <TableCell>
                  <StatusBadge kind="validation" value={version.validation_status} />
                </TableCell>
                <TableCell className="font-mono text-xs">{version.created_by ? shortId(version.created_by) : "-"}</TableCell>
                <TableCell className="font-mono text-xs">{version.approved_by ? shortId(version.approved_by) : "-"}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{formatDateTime(version.activated_at)}</TableCell>
                <TableCell className="text-right">
                  <Link href={`/aturan/${version.id}`} className="text-sm text-brand underline-offset-4 hover:underline">
                    Buka
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </SectionCard>
  );
}

export function RuleSetsView() {
  const ruleSets = useApi<RuleSet[]>("/v1/rule-sets");
  return (
    <RequirePermission permission="rule:read">
      <div className="space-y-6">
        <PageHeader
          title="Aturan bukti"
          description="Expected evidence per vektor risiko, berversi dan disetujui pihak yang berbeda dari penyusunnya. Aturan aktif tidak pernah diubah langsung."
        />
        <Alert variant="warning">
          <AlertTitle>Aturan domain belum divalidasi pakar</AlertTitle>
          <AlertDescription>
            Aturan berstatus &ldquo;belum tervalidasi&rdquo; atau &ldquo;simulasi&rdquo; bukan aturan klinis resmi. Aturan yang belum
            divalidasi pakar casemix/RMIK dibatasi pada tier T1 dan tidak dapat menjadi dasar rekomendasi tinjauan.
          </AlertDescription>
        </Alert>
        <QueryBoundary state={ruleSets} rows={5}>
          {(items) => (
            <div className="space-y-6">
              {items.map((ruleSet) => (
                <RuleSetCard key={ruleSet.id} ruleSet={ruleSet} reload={ruleSets.reload} />
              ))}
            </div>
          )}
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

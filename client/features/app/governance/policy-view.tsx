"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { PolicyVersion } from "@/lib/api-types";
import { formatDateTime, shortId } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { KeyValueList } from "../shared/key-value";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";
import { ActionButton } from "./action-button";
import { describeCondition } from "./describe-condition";
import { CreatePolicyDialog, PreviewPolicyDialog } from "./policy-dialogs";

function PolicyActions({ policy, reload }: { policy: PolicyVersion; reload: () => void }) {
  const { can, principal } = useAuth();
  const base = `/v1/policy-versions/${policy.id}`;
  const author = policy.created_by === principal.user_id;
  return (
    <>
      <PreviewPolicyDialog policy={policy} />
      {can("rule:write") && policy.status === "draft" ? (
        <ActionButton
          label="Ajukan persetujuan"
          variant="brand"
          title="Ajukan kebijakan untuk persetujuan?"
          description="Server memvalidasi kebijakan: wajib ada aturan T0, T0 mendahului T1-T3, dan aturan terakhir berupa penampung."
          path={`${base}/submit`}
          onDone={reload}
        />
      ) : null}
      {can("rule:approve") && policy.status === "pending_approval" ? (
        <>
          <ActionButton
            label="Setujui"
            variant="brand"
            disabled={author}
            title="Setujui versi kebijakan?"
            description="Penyusun tidak dapat menyetujui kebijakannya sendiri."
            path={`${base}/approve`}
            onDone={reload}
          />
          <ActionButton
            label="Tolak"
            variant="destructive"
            tone="destructive"
            withReason
            title="Tolak versi kebijakan?"
            description="Versi yang ditolak tidak dapat diaktifkan."
            path={`${base}/reject`}
            onDone={reload}
          />
        </>
      ) : null}
      {can("rule:approve") && policy.status === "approved" ? (
        <ActionButton
          label="Aktifkan"
          variant="brand"
          title="Aktifkan versi kebijakan?"
          description="Hanya satu kebijakan yang aktif. Versi aktif sebelumnya dipensiunkan, dan semua pemeriksaan berikutnya memakai versi ini."
          path={`${base}/activate`}
          onDone={reload}
        />
      ) : null}
      {can("rule:approve") && policy.status === "active" ? (
        <ActionButton
          label="Pensiunkan"
          variant="destructive"
          tone="destructive"
          title="Pensiunkan kebijakan aktif?"
          description="Tanpa kebijakan aktif, pemeriksaan tidak dapat menetapkan tier sampai versi lain diaktifkan."
          path={`${base}/retire`}
          onDone={reload}
        />
      ) : null}
    </>
  );
}

function PolicyCard({ policy, reload }: { policy: PolicyVersion; reload: () => void }) {
  const rules = [...policy.rules].sort((a, b) => a.priority - b.priority);
  return (
    <SectionCard
      title={`Kebijakan ${policy.version}`}
      actions={<PolicyActions policy={policy} reload={reload} />}
      description="Aturan dievaluasi berurutan menurut prioritas; aturan pertama yang cocok menetapkan tier."
    >
      <KeyValueList
        columns={3}
        className="mb-4"
        items={[
          { label: "Status", value: <StatusBadge kind="version" value={policy.status} /> },
          { label: "Hash konfigurasi", value: <span className="font-mono text-xs" title={policy.config_hash}>{shortId(policy.config_hash)}</span> },
          { label: "Disusun oleh", value: policy.created_by ? <span className="font-mono text-xs">{shortId(policy.created_by)}</span> : "-" },
          { label: "Disetujui", value: `${formatDateTime(policy.approved_at)}${policy.approved_by ? ` oleh ${shortId(policy.approved_by)}` : ""}` },
          { label: "Diaktifkan", value: formatDateTime(policy.activated_at) },
        ]}
      />
      <div className="overflow-x-auto rounded-2xl border border-line">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-right">Prioritas</TableHead>
              <TableHead>Kode aturan</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Kondisi</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rules.map((rule) => (
              <TableRow key={rule.id}>
                <TableCell className="text-right tabular-nums">{rule.priority}</TableCell>
                <TableCell className="font-mono text-xs">{rule.code}</TableCell>
                <TableCell>
                  <TierBadge tier={rule.tier} compact />
                </TableCell>
                <TableCell className="whitespace-normal">
                  <ul className="space-y-0.5 text-xs">
                    {describeCondition(rule.condition).map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </SectionCard>
  );
}

export function PolicyView() {
  const { can } = useAuth();
  const policies = useApi<PolicyVersion[]>("/v1/policy-versions");
  const template = policies.data?.find((policy) => policy.status === "active") ?? policies.data?.[0] ?? null;

  return (
    <RequirePermission permission="rule:read">
      <div className="space-y-6">
        <PageHeader
          title="Kebijakan tier"
          description="Aturan deterministik yang menetapkan T0 abstain, T1 inform, T2 recommend review, dan T3 flag for human verdict. Model bahasa tidak memilih tier."
          actions={can("rule:write") ? <CreatePolicyDialog template={template} onDone={policies.reload} /> : null}
        />
        <Alert variant="info">
          <AlertTitle>Abstain mendahului penilaian risiko</AlertTitle>
          <AlertDescription>
            Bila sumber bukti tidak memadai, ada konflik bukti yang belum selesai, atau sitasi tidak dapat diverifikasi,
            hasilnya T0. Tidak ada tier yang menolak atau mengubah klaim secara otomatis.
          </AlertDescription>
        </Alert>
        <QueryBoundary state={policies} rows={5}>
          {(items) => (
            <div className="space-y-6">
              {items.map((policy) => (
                <PolicyCard key={policy.id} policy={policy} reload={policies.reload} />
              ))}
            </div>
          )}
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

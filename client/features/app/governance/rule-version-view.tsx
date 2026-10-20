"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeftIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { buttonVariants } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import type { RuleVersion } from "@/lib/api-types";
import { formatDateTime, shortId } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { VECTOR_LABELS, labelOf } from "../shared/labels";
import { KeyValueList } from "../shared/key-value";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { ActionButton } from "./action-button";
import { ApproveDialog } from "./approve-dialog";
import { SpecView } from "./spec-view";

function Actions({ version, reload }: { version: RuleVersion; reload: () => void }) {
  const { can, principal } = useAuth();
  const base = `/v1/rule-versions/${version.id}`;
  const author = version.created_by === principal.user_id;
  return (
    <>
      {can("rule:write") && version.status === "draft" ? (
        <ActionButton
          label="Ajukan persetujuan"
          variant="brand"
          title="Ajukan versi aturan untuk persetujuan?"
          description="Setelah diajukan, versi tidak dapat diedit. Persetujuan harus dilakukan pihak lain."
          path={`${base}/submit`}
          onDone={reload}
        />
      ) : null}
      {can("rule:approve") && version.status === "pending_approval" ? (
        <>
          <ApproveDialog
            path={`${base}/approve`}
            title="Setujui versi aturan"
            description="Persetujuan dicatat atas nama Anda. Penyusun versi tidak dapat menyetujui versinya sendiri."
            disabled={author}
            disabledReason="Penyusun tidak boleh menyetujui versinya sendiri"
            onDone={reload}
          />
          <ActionButton
            label="Tolak"
            tone="destructive"
            variant="destructive"
            withReason
            title="Tolak versi aturan?"
            description="Versi yang ditolak tidak dapat diaktifkan."
            path={`${base}/reject`}
            onDone={reload}
          />
        </>
      ) : null}
      {can("rule:approve") && version.status === "approved" ? (
        <ActionButton
          label="Aktifkan"
          variant="brand"
          title="Aktifkan versi aturan?"
          description="Versi aktif sebelumnya pada rule set ini dipensiunkan. Pemeriksaan berikutnya memakai versi ini; hasil lama tetap tercatat dengan versi yang dipakainya."
          path={`${base}/activate`}
          onDone={reload}
        />
      ) : null}
      {can("rule:approve") && version.status === "active" ? (
        <ActionButton
          label="Pensiunkan"
          tone="destructive"
          variant="destructive"
          title="Pensiunkan versi aktif?"
          description="Tanpa versi aktif, pemeriksaan untuk vektor ini tidak dapat berjalan sampai versi lain diaktifkan."
          path={`${base}/retire`}
          onDone={reload}
        />
      ) : null}
    </>
  );
}

function Body({ version }: { version: RuleVersion }) {
  return (
    <div className="space-y-6">
      <SectionCard title="Ringkasan versi">
        <KeyValueList
          columns={3}
          items={[
            { label: "Rule set", value: version.rule_set_name },
            { label: "Vektor risiko", value: labelOf(VECTOR_LABELS, version.vector_code) },
            { label: "Versi", value: version.version },
            { label: "Status", value: <StatusBadge kind="version" value={version.status} /> },
            { label: "Validasi", value: <StatusBadge kind="validation" value={version.validation_status} /> },
            { label: "Disusun oleh", value: version.created_by ? <span className="font-mono text-xs">{shortId(version.created_by)}</span> : "-" },
            { label: "Diajukan", value: formatDateTime(version.submitted_at) },
            { label: "Disetujui", value: `${formatDateTime(version.approved_at)}${version.approved_by ? ` oleh ${shortId(version.approved_by)}` : ""}` },
            { label: "Diaktifkan", value: formatDateTime(version.activated_at) },
            { label: "Dipensiunkan", value: formatDateTime(version.retired_at) },
          ]}
        />
      </SectionCard>
      <SectionCard title={`Expected rule (${version.expected_rules.length})`} description="Pola kode klaim dan bukti yang diharapkan ada.">
        <div className="space-y-4">
          {version.expected_rules.map((rule) => (
            <div key={rule.id} className="rounded-2xl border border-line p-4">
              <p className="mb-2 text-sm">
                <span className="text-muted-foreground">Pola kode: </span>
                <span className="font-mono text-xs font-medium">{rule.code_pattern}</span>
              </p>
              <SpecView spec={rule.spec} />
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

export function RuleVersionView() {
  const { id } = useParams<{ id: string }>();
  const state = useApi<RuleVersion>(`/v1/rule-versions/${id}`);
  return (
    <RequirePermission permission="rule:read">
      <div className="space-y-6">
        <PageHeader
          title={state.data ? `Aturan ${state.data.rule_set_name} ${state.data.version}` : "Versi aturan"}
          description="Spesifikasi expected evidence dan siklus persetujuannya."
          actions={
            <>
              <Link href="/aturan" className={buttonVariants({ variant: "outline", size: "sm" })}>
                <ArrowLeftIcon aria-hidden="true" />
                Semua aturan
              </Link>
              {state.data ? <Actions version={state.data} reload={state.reload} /> : null}
            </>
          }
        />
        <QueryBoundary state={state} rows={5}>
          {(version) => <Body version={version} />}
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

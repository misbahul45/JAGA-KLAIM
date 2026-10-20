"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeftIcon, LockIcon, TriangleAlertIcon } from "lucide-react";
import type { ReactNode } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import type { InterventionDetail } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { CODE_TYPE_LABELS, VECTOR_LABELS, VERDICT_LABELS, labelOf } from "../shared/labels";
import { EvidenceList } from "../shared/evidence-list";
import { KeyValueList } from "../shared/key-value";
import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";
import { AssessmentStep } from "./assessment-step";
import { ProposeUpdateDialog } from "./propose-update-dialog";
import { RecommendationPanel } from "./recommendation-panel";
import { VerdictForm, VerdictHistory, currentVerdict } from "./verdict-step";

const ELIGIBLE_FOR_RULE_UPDATE = new Set(["does_not_support_finding", "insufficient_evidence"]);

function Locked({ title, text }: { title: string; text: string }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-dashed border-line bg-surface p-4">
      <LockIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-ink">{title}</p>
        <p className="text-sm text-muted-foreground">{text}</p>
      </div>
    </div>
  );
}

function Step({ index, title, children }: { index: number; title: string; children: ReactNode }) {
  return (
    <SectionCard title={`Langkah ${index} · ${title}`}>
      {children}
    </SectionCard>
  );
}

function Workbench({ detail, reload }: { detail: InterventionDetail; reload: () => void }) {
  const { can } = useAuth();
  const gated = detail.gate.required;
  const revealed = detail.gate.revealed;
  const canAct = !detail.stale && detail.claim.status !== "locked";
  const verdict = currentVerdict(detail.verdicts);
  const resolved = detail.resolved_at !== null;
  const cited = new Set(detail.recommendation?.citations.map((citation) => citation.evidence_item_id) ?? []);
  const offset = gated ? 1 : 0;

  return (
    <div className="space-y-6">
      {detail.stale ? (
        <Alert variant="warning">
          <TriangleAlertIcon aria-hidden="true" />
          <AlertTitle>Hasil pemeriksaan ini sudah tidak berlaku</AlertTitle>
          <AlertDescription>
            Klaim berubah atau diperiksa ulang setelah hasil ini dibuat. Penilaian dan verdict baru tidak dapat dicatat.
          </AlertDescription>
        </Alert>
      ) : null}
      {detail.evidence_updated_after_run ? (
        <Alert variant="warning">
          <TriangleAlertIcon aria-hidden="true" />
          <AlertTitle>Bukti diperbarui setelah pemeriksaan ini</AlertTitle>
          <AlertDescription>Pertimbangkan meminta pemeriksaan ulang dari halaman klaim.</AlertDescription>
        </Alert>
      ) : null}

      <SectionCard
        title="Klaim yang ditinjau"
        actions={
          <Link href={`/klaim/${detail.claim.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
            Buka klaim
          </Link>
        }
      >
        <KeyValueList
          columns={3}
          items={[
            { label: "Episode", value: detail.claim.episode_no },
            { label: "Status klaim", value: <StatusBadge kind="claim" value={detail.claim.status} /> },
            { label: "Vektor risiko", value: labelOf(VECTOR_LABELS, detail.vector_code) },
            { label: "Versi aturan", value: detail.run.rule_version },
            { label: "Validasi aturan", value: <StatusBadge kind="validation" value={detail.run.rule_validation_status} /> },
            { label: "Versi kebijakan", value: detail.run.policy_version },
            {
              label: "Kode klaim",
              value: (
                <span className="flex flex-wrap gap-1.5">
                  {detail.claim.codes.map((code) => (
                    <span key={code.id} className="rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-xs">
                      {labelOf(CODE_TYPE_LABELS, code.code_type)} {code.code}
                    </span>
                  ))}
                </span>
              ),
            },
            { label: "Dibuat", value: formatDateTime(detail.created_at) },
            {
              label: "Rincian pemeriksaan",
              value: (
                <Link href={`/pemeriksaan/${detail.run.id}`} className="text-brand underline-offset-4 hover:underline">
                  Lihat langkah dan cakupan
                </Link>
              ),
            },
          ]}
        />
      </SectionCard>

      <SectionCard
        title="Bukti yang tersedia"
        description="Tinjau bukti terlebih dahulu. Bukti tidak ditemukan tidak membuktikan pelayanan tidak dilakukan."
      >
        <EvidenceList items={detail.evidence} highlightIds={cited} />
      </SectionCard>

      {gated ? (
        <Step index={1} title="Penilaian mandiri">
          {detail.gate.own_assessment ? (
            <div className="space-y-1 text-sm">
              <p className="font-medium text-ink">
                {labelOf(VERDICT_LABELS, detail.gate.own_assessment.self_verdict)}
              </p>
              {detail.gate.own_assessment.self_note ? (
                <p className="whitespace-pre-wrap text-ink/90">{detail.gate.own_assessment.self_note}</p>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Tersimpan {formatDateTime(detail.gate.own_assessment.submitted_at)} dan tidak dapat diubah.
              </p>
            </div>
          ) : can("review:assess") && canAct && !resolved ? (
            <AssessmentStep interventionId={detail.id} onSaved={reload} />
          ) : (
            <p className="text-sm text-muted-foreground">
              Penilaian mandiri belum dicatat dan tidak dapat dibuat pada kondisi ini.
            </p>
          )}
        </Step>
      ) : null}

      <Step index={1 + offset} title="Rekomendasi sistem">
        {revealed ? (
          <RecommendationPanel detail={detail} />
        ) : (
          <Locked
            title="Rekomendasi sistem terkunci"
            text="Simpan penilaian mandiri Anda pada langkah 1. Setelah itu temuan, sitasi, dan saran tindakan terbuka."
          />
        )}
      </Step>

      <Step index={2 + offset} title="Verdict manusia">
        {!revealed ? (
          <Locked
            title="Verdict belum dapat dicatat"
            text="Buka rekomendasi sistem terlebih dahulu dengan menyimpan penilaian mandiri."
          />
        ) : (
          <div className="space-y-5">
            <VerdictHistory verdicts={detail.verdicts} />
            {!can("review:verdict") ? (
              <p className="text-sm text-muted-foreground">Peran Anda tidak dapat mencatat verdict.</p>
            ) : !canAct ? (
              <p className="text-sm text-muted-foreground">Verdict tidak dapat dicatat pada hasil ini.</p>
            ) : !resolved ? (
              <VerdictForm interventionId={detail.id} correction={false} onSaved={reload} />
            ) : (
              <details className="rounded-2xl border border-line p-4">
                <summary className="cursor-pointer text-sm font-medium text-ink">Koreksi verdict</summary>
                <div className="mt-4">
                  <VerdictForm interventionId={detail.id} correction initial={verdict} onSaved={reload} />
                </div>
              </details>
            )}
            {resolved && verdict && ELIGIBLE_FOR_RULE_UPDATE.has(verdict.verdict) && can("rule_update:propose") ? (
              <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-lavender/50 p-4 text-sm">
                <p className="min-w-0 flex-1 text-ink">
                  Verdict ini dapat menjadi dasar proposal pembaruan aturan. Proposal tidak mengubah aturan aktif.
                </p>
                <ProposeUpdateDialog verdictId={verdict.id} ruleVersionId={detail.run.rule_version_id} />
              </div>
            ) : null}
          </div>
        )}
      </Step>
    </div>
  );
}

export function WorkbenchView() {
  const { id } = useParams<{ id: string }>();
  const state = useApi<InterventionDetail>(`/v1/interventions/${id}`);

  return (
    <RequirePermission permission="review:read">
      <div className="space-y-6">
        <PageHeader
          title="Workbench verifikator"
          description="Bukti lebih dulu, penilaian mandiri kedua, rekomendasi sistem ketiga, lalu keputusan Anda."
          actions={
            <>
              {state.data ? <TierBadge tier={state.data.tier} /> : null}
              <Link href="/tinjauan" className={buttonVariants({ variant: "outline", size: "sm" })}>
                <ArrowLeftIcon aria-hidden="true" />
                Antrean
              </Link>
            </>
          }
        />
        <QueryBoundary state={state} rows={6}>
          {(detail) => <Workbench detail={detail} reload={state.reload} />}
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

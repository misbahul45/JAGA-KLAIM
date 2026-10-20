"use client";

import Link from "next/link";
import { PlusIcon, RefreshCwIcon, TriangleAlertIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import type { Dashboard } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { STATUS_TABLES, type StatusKind } from "../shared/labels";
import { QueryBoundary } from "../shared/query-boundary";
import { SectionCard } from "../shared/section-card";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";

type StatTileProps = {
  label: string;
  value: number;
  hint: string;
  href?: string;
};

function StatTile({ label, value, hint, href }: StatTileProps) {
  const body = (
    <div className="h-full rounded-3xl border border-line bg-white p-5 transition-colors hover:border-brand/40">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-[-0.03em] text-ink tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
  return href ? (
    <Link href={href} className="block rounded-3xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
      {body}
    </Link>
  ) : (
    body
  );
}

function CountList({ kind, counts }: { kind: StatusKind; counts: Record<string, number> }) {
  const order = Object.keys(STATUS_TABLES[kind]);
  const known = order.filter((key) => counts[key] !== undefined);
  const extra = Object.keys(counts).filter((key) => !order.includes(key));
  const keys = [...known, ...extra];
  if (keys.length === 0) {
    return <p className="text-sm text-muted-foreground">Belum ada data.</p>;
  }
  return (
    <ul className="divide-y divide-line">
      {keys.map((key) => (
        <li key={key} className="flex items-center justify-between py-2 text-sm">
          <StatusBadge kind={kind} value={key} />
          <span className="font-medium text-ink tabular-nums">{counts[key]}</span>
        </li>
      ))}
    </ul>
  );
}

function SourceHealth({ sources }: { sources: Dashboard["sources"] }) {
  if (sources.length === 0) {
    return <p className="text-sm text-muted-foreground">Belum ada sumber bukti terdaftar.</p>;
  }
  return (
    <ul className="divide-y divide-line">
      {sources.map((source) => (
        <li key={source.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
          <div className="min-w-0">
            <p className="font-medium text-ink">{source.system_ref}</p>
            <p className="text-xs text-muted-foreground">
              {source.source_type} · sinkronisasi terakhir {formatDateTime(source.last_synced_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!source.is_enabled ? <StatusBadge kind="job" value="cancelled" className="opacity-80" /> : null}
            <StatusBadge kind="health" value={source.health_status} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function Overview({ data }: { data: Dashboard }) {
  const { can } = useAuth();
  const t2 = data.open_review_by_tier["T2"] ?? 0;
  const t3 = data.open_review_by_tier["T3"] ?? 0;
  const underReview = data.claims_by_status["under_review"] ?? 0;
  const waiting = (data.jobs_by_status["queued"] ?? 0) + (data.jobs_by_status["processing"] ?? 0);
  const impaired = data.sources.filter((source) => source.is_enabled && source.health_status !== "healthy");
  const reviewHref = can("review:read") ? "/tinjauan" : undefined;

  return (
    <div className="space-y-6">
      {impaired.length > 0 ? (
        <Alert variant="warning">
          <TriangleAlertIcon aria-hidden="true" />
          <AlertTitle>Sumber bukti belum sepenuhnya sehat</AlertTitle>
          <AlertDescription>
            {impaired
              .map((source) => `${source.system_ref} (${STATUS_TABLES.health[source.health_status]?.label ?? source.health_status})`)
              .join(", ")}.
            Pemeriksaan yang bergantung pada sumber ini dapat berakhir abstain (T0) karena bukti tidak
            ditemukan tidak berarti pelayanan tidak terjadi.
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Perlu tinjauan T3" value={t3} hint="Menunggu verifikasi manusia" href={reviewHref} />
        <StatTile label="Perlu tinjauan T2" value={t2} hint="Pemeriksaan tambahan disarankan" href={reviewHref} />
        <StatTile label="Klaim dalam tinjauan" value={underReview} hint="Status klaim: dalam tinjauan" href="/klaim?status=under_review" />
        <StatTile label="Pemeriksaan berjalan" value={waiting} hint="Job mengantre atau diproses" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Klaim menurut status" description="Seluruh klaim pada faskes Anda.">
          <CountList kind="claim" counts={data.claims_by_status} />
        </SectionCard>
        <SectionCard title="Hasil pemeriksaan 30 hari" description="Satu hasil per vektor risiko per pemeriksaan.">
          <CountList kind="outcome" counts={data.run_outcomes_30d} />
        </SectionCard>
        <SectionCard title="Antrean job pemeriksaan" description="Job dibuat saat coding dikirim atau diperiksa ulang.">
          <CountList kind="job" counts={data.jobs_by_status} />
        </SectionCard>
        <SectionCard
          title="Kesehatan sumber bukti"
          description="Status dilaporkan operator faskes; belum ada konektor otomatis."
          actions={
            can("source:read") ? (
              <Link href="/sumber-bukti" className={buttonVariants({ variant: "outline", size: "sm" })}>
                Kelola
              </Link>
            ) : null
          }
        >
          <SourceHealth sources={data.sources} />
        </SectionCard>
      </div>

      <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        Tier:
        <TierBadge tier="T0" compact /> abstain
        <TierBadge tier="T1" compact /> inform
        <TierBadge tier="T2" compact /> recommend review
        <TierBadge tier="T3" compact /> flag for human verdict. Sistem tidak menolak atau mengubah klaim.
      </p>
    </div>
  );
}

export function DashboardView() {
  const { can } = useAuth();
  const state = useApi<Dashboard>("/v1/dashboard");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dasbor"
        description="Ringkasan alur pra-klaim di faskes Anda. Semua angka dihitung dari data sistem pada saat dimuat."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={state.reload} disabled={state.refreshing}>
              <RefreshCwIcon aria-hidden="true" />
              Muat ulang
            </Button>
            {can("claim:write") ? (
              <Link href="/klaim/baru" className={buttonVariants({ variant: "brand", size: "sm" })}>
                <PlusIcon aria-hidden="true" />
                Klaim baru
              </Link>
            ) : null}
          </>
        }
      />
      <QueryBoundary state={state} rows={6}>
        {(data) => <Overview data={data} />}
      </QueryBoundary>
    </div>
  );
}

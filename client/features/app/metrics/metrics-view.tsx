"use client";

import { useState } from "react";

import { OptionSelect } from "@/components/shared/option-select";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";
import { toQuery } from "@/lib/api";
import type { Metric } from "@/lib/api-types";
import { formatDateTime, formatDuration, formatNumber, formatPercent } from "@/lib/format";

import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";

const WINDOWS = [
  { value: "default", label: "30 hari terakhir (bawaan)" },
  { value: "7", label: "7 hari terakhir" },
  { value: "90", label: "90 hari terakhir" },
];

type WindowRange = { start: string; end: string } | null;

function formatValue(metric: Metric): string {
  if (metric.value === null) return "-";
  if (metric.unit === "ratio") return formatPercent(metric.value);
  if (metric.unit === "seconds") return formatDuration(metric.value * 1000);
  if (metric.unit === "alerts_per_hour") return `${formatNumber(metric.value, 2)} / jam`;
  return formatNumber(metric.value);
}

const STATUS_BADGE: Record<Metric["status"], { label: string; variant: "success" | "neutral" | "warning" }> = {
  ok: { label: "Terukur", variant: "success" },
  no_data: { label: "Belum ada data", variant: "neutral" },
  not_measured: { label: "Belum diukur", variant: "warning" },
};

function MetricCard({ metric }: { metric: Metric }) {
  const badge = STATUS_BADGE[metric.status];
  const breakdown = Object.entries(metric.breakdown);
  return (
    <article className="flex flex-col rounded-3xl border border-line bg-white p-5">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">{metric.label}</h2>
        <Badge variant={badge.variant}>{badge.label}</Badge>
      </div>
      <p className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-ink tabular-nums">{formatValue(metric)}</p>
      <p className="mt-2 text-sm text-muted-foreground">{metric.definition}</p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <dt className="text-muted-foreground">Pembilang / penyebut</dt>
          <dd className="font-medium text-ink tabular-nums">
            {metric.numerator === null ? "-" : formatNumber(metric.numerator)} /{" "}
            {metric.denominator === null ? "-" : formatNumber(metric.denominator)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Jumlah sampel</dt>
          <dd className="font-medium text-ink tabular-nums">{metric.sample_size}</dd>
        </div>
      </dl>
      {breakdown.length > 0 ? (
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer text-muted-foreground">Rincian</summary>
          <pre className="mt-1 overflow-x-auto rounded-xl bg-surface p-2">{JSON.stringify(metric.breakdown, null, 2)}</pre>
        </details>
      ) : null}
      {metric.note ? <p className="mt-3 text-xs text-muted-foreground">{metric.note}</p> : null}
      {metric.target ? (
        <p className="mt-3 rounded-xl bg-surface px-3 py-2 text-xs text-muted-foreground">{metric.target}</p>
      ) : null}
      <p className="mt-3 text-[0.7rem] text-muted-foreground">
        Periode {formatDateTime(metric.window_start)} sampai {formatDateTime(metric.window_end)}
      </p>
    </article>
  );
}

export function MetricsView() {
  const [windowKey, setWindowKey] = useState("default");
  const [range, setRange] = useState<WindowRange>(null);
  const metrics = useApi<Metric[]>(`/v1/metrics${range ? toQuery({ window_start: range.start, window_end: range.end }) : ""}`);

  const choose = (value: string) => {
    setWindowKey(value);
    if (value === "default") {
      setRange(null);
      return;
    }
    const end = new Date();
    const start = new Date(end.getTime() - Number(value) * 24 * 3600 * 1000);
    setRange({ start: start.toISOString(), end: end.toISOString() });
  };

  return (
    <RequirePermission permission="metrics:read">
      <div className="space-y-6">
        <PageHeader
          title="Metrik mutu"
          description="Setiap angka menampilkan definisi, denominator, periode, dan jumlah sampel. Target adalah hipotesis awal yang masih harus divalidasi, bukan hasil yang sudah tercapai."
          actions={
            <div className="w-56">
              <OptionSelect ariaLabel="Periode" value={windowKey} options={WINDOWS} onChange={choose} />
            </div>
          }
        />
        <Alert variant="info">
          <AlertTitle>Cara membaca</AlertTitle>
          <AlertDescription>
            Baca Precision (proksi) bersama Abstention Rate agar menaikkan abstain tidak dipakai sebagai jalan
            pintas. Citation Fidelity mengukur integritas teknis sitasi, bukan kebenaran klinis. Presisi sebenarnya
            memerlukan penilaian ahli casemix/RMIK. Metrik kesetaraan perlakuan antar-faskes belum tersedia.
          </AlertDescription>
        </Alert>
        <QueryBoundary state={metrics} rows={6}>
          {(items) => (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {items.map((metric) => (
                <MetricCard key={metric.code} metric={metric} />
              ))}
            </div>
          )}
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

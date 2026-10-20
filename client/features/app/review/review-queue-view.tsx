"use client";

import Link from "next/link";
import { useState } from "react";
import { ClipboardCheckIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { OptionSelect } from "@/components/shared/option-select";
import { PageHeader } from "@/components/shared/page-header";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import { toQuery } from "@/lib/api";
import type { Page, QueueItem } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

import { RequirePermission } from "../shared/require-permission";
import { VECTOR_LABELS, labelOf } from "../shared/labels";
import { QueryBoundary } from "../shared/query-boundary";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";
import { buttonVariants } from "@/components/ui/button";

const PAGE_SIZE = 15;
const ALL = "all";

const TIER_OPTIONS = [
  { value: ALL, label: "T2 dan T3" },
  { value: "T3", label: "T3 Flag for Human Verdict" },
  { value: "T2", label: "T2 Recommend Review" },
];
const STATE_OPTIONS = [
  { value: "open", label: "Belum diputuskan" },
  { value: "resolved", label: "Sudah diputuskan" },
  { value: "all", label: "Semua" },
];
const VECTOR_OPTIONS = [
  { value: ALL, label: "Semua vektor" },
  ...Object.entries(VECTOR_LABELS).map(([value, label]) => ({ value, label })),
];

export function ReviewQueueView() {
  const [tier, setTier] = useState(ALL);
  const [state, setState] = useState("open");
  const [vector, setVector] = useState(ALL);
  const [page, setPage] = useState(1);

  const queue = useApi<Page<QueueItem>>(
    `/v1/interventions${toQuery({
      tier: tier === ALL ? undefined : tier,
      state,
      vector: vector === ALL ? undefined : vector,
      page,
      page_size: PAGE_SIZE,
    })}`,
  );

  const change = (apply: () => void) => {
    apply();
    setPage(1);
  };

  return (
    <RequirePermission permission="review:read">
      <div className="space-y-6">
        <PageHeader
          title="Antrean tinjauan"
          description="Ketidaksesuaian yang menunggu verifikasi manusia. Penilaian mandiri wajib disimpan sebelum rekomendasi sistem dibuka. Keputusan akhir selalu ada pada verifikator."
        />

        <div className="grid gap-3 rounded-3xl border border-line bg-white p-4 sm:grid-cols-3">
          <OptionSelect ariaLabel="Filter tier" value={tier} options={TIER_OPTIONS} onChange={(value) => change(() => setTier(value))} />
          <OptionSelect ariaLabel="Filter keputusan" value={state} options={STATE_OPTIONS} onChange={(value) => change(() => setState(value))} />
          <OptionSelect ariaLabel="Filter vektor risiko" value={vector} options={VECTOR_OPTIONS} onChange={(value) => change(() => setVector(value))} />
        </div>

        <QueryBoundary state={queue} rows={5}>
          {(data) =>
            data.items.length === 0 ? (
              <EmptyState
                icon={ClipboardCheckIcon}
                title="Tidak ada butir tinjauan"
                description="Belum ada ketidaksesuaian T2 atau T3 yang cocok dengan filter. Klaim tanpa selisih bukti dicatat sebagai No Action pada audit trail."
              />
            ) : (
              <div className="space-y-3">
                <div className="overflow-x-auto rounded-3xl border border-line bg-white">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Tier</TableHead>
                        <TableHead>Vektor</TableHead>
                        <TableHead>Klaim</TableHead>
                        <TableHead>Status klaim</TableHead>
                        <TableHead>Dibuat</TableHead>
                        <TableHead>Penilaian mandiri Anda</TableHead>
                        <TableHead className="text-right">Aksi</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.items.map((item) => (
                        <TableRow key={item.intervention_id}>
                          <TableCell>
                            <TierBadge tier={item.tier} compact />
                          </TableCell>
                          <TableCell>{labelOf(VECTOR_LABELS, item.vector_code)}</TableCell>
                          <TableCell>
                            <Link href={`/klaim/${item.claim_id}`} className="font-medium text-brand underline-offset-4 hover:underline">
                              {item.episode_no}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <StatusBadge kind="claim" value={item.claim_status} />
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">{formatDateTime(item.created_at)}</TableCell>
                          <TableCell>
                            {item.resolved_at ? (
                              <Badge variant="success">Diputuskan {formatDateTime(item.resolved_at)}</Badge>
                            ) : item.assessed_by_me ? (
                              <Badge variant="info">Tersimpan</Badge>
                            ) : (
                              <Badge variant="neutral">Belum</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Link
                              href={`/tinjauan/${item.intervention_id}`}
                              className={buttonVariants({ variant: item.resolved_at ? "outline" : "brand", size: "sm" })}
                            >
                              {item.resolved_at ? "Lihat" : "Tinjau"}
                            </Link>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <PaginationBar page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
              </div>
            )
          }
        </QueryBoundary>
      </div>
    </RequirePermission>
  );
}

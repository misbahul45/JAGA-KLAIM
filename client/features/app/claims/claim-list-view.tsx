"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { FileTextIcon, PlusIcon, SearchIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { OptionSelect } from "@/components/shared/option-select";
import { PageHeader } from "@/components/shared/page-header";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { Input } from "@/components/ui/input";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { toQuery } from "@/lib/api";
import type { ClaimListItem, Page } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

import { useAuth } from "../auth/auth-context";
import { STATUS_TABLES, VECTOR_LABELS } from "../shared/labels";
import { QueryBoundary } from "../shared/query-boundary";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";

const PAGE_SIZE = 15;
const ALL = "all";

const STATUS_OPTIONS = [
  { value: ALL, label: "Semua status" },
  ...Object.entries(STATUS_TABLES.claim).map(([value, entry]) => ({ value, label: entry.label })),
];
const TIER_OPTIONS = [
  { value: ALL, label: "Semua tier terbuka" },
  { value: "T3", label: "T3 Flag for Human Verdict" },
  { value: "T2", label: "T2 Recommend Review" },
  { value: "T1", label: "T1 Inform" },
  { value: "T0", label: "T0 Abstain" },
];
const VECTOR_OPTIONS = [
  { value: ALL, label: "Semua vektor" },
  ...Object.entries(VECTOR_LABELS).map(([value, label]) => ({ value, label })),
];
const SORT_OPTIONS = [
  { value: "updated_at", label: "Terakhir diperbarui" },
  { value: "created_at", label: "Tanggal dibuat" },
  { value: "episode_no", label: "Nomor episode" },
  { value: "status", label: "Status" },
];
const ORDER_OPTIONS = [
  { value: "desc", label: "Terbaru / Z-A" },
  { value: "asc", label: "Terlama / A-Z" },
];

function statusFromQuery(value: string | null): string {
  return value && value in STATUS_TABLES.claim ? value : ALL;
}

export function ClaimListView() {
  const { can } = useAuth();
  const params = useSearchParams();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(() => statusFromQuery(params.get("status")));
  const [tier, setTier] = useState(ALL);
  const [vector, setVector] = useState(ALL);
  const [sort, setSort] = useState("updated_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const query = useDebouncedValue(search.trim());

  const state = useApi<Page<ClaimListItem>>(
    `/v1/claims${toQuery({
      q: query,
      status: status === ALL ? undefined : status,
      tier: tier === ALL ? undefined : tier,
      vector: vector === ALL ? undefined : vector,
      sort,
      order,
      page,
      page_size: PAGE_SIZE,
    })}`,
  );

  const change = (apply: () => void) => {
    apply();
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Klaim"
        description="Daftar klaim pada faskes Anda. Pencarian, filter, urutan, dan halaman diproses di server."
        actions={
          can("claim:write") ? (
            <Link href="/klaim/baru" className={buttonVariants({ variant: "brand", size: "sm" })}>
              <PlusIcon aria-hidden="true" />
              Klaim baru
            </Link>
          ) : null
        }
      />

      <div className="grid gap-3 rounded-3xl border border-line bg-white p-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="relative sm:col-span-2 lg:col-span-3">
          <SearchIcon
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            aria-label="Cari nomor episode atau pseudonim pasien"
            placeholder="Cari nomor episode atau pseudonim"
            className="pl-8"
            value={search}
            onChange={(event) => change(() => setSearch(event.target.value))}
          />
        </div>
        <OptionSelect ariaLabel="Filter status" value={status} options={STATUS_OPTIONS} onChange={(value) => change(() => setStatus(value))} />
        <OptionSelect ariaLabel="Filter tier tinjauan terbuka" value={tier} options={TIER_OPTIONS} onChange={(value) => change(() => setTier(value))} />
        <OptionSelect ariaLabel="Filter vektor risiko" value={vector} options={VECTOR_OPTIONS} onChange={(value) => change(() => setVector(value))} />
        <OptionSelect ariaLabel="Urutkan menurut" value={sort} options={SORT_OPTIONS} onChange={(value) => change(() => setSort(value))} />
        <OptionSelect ariaLabel="Arah urutan" value={order} options={ORDER_OPTIONS} onChange={(value) => change(() => setOrder(value))} />
      </div>

      <QueryBoundary state={state} rows={6}>
        {(data) =>
          data.items.length === 0 ? (
            <EmptyState
              icon={FileTextIcon}
              title="Tidak ada klaim yang cocok"
              description="Ubah filter atau kata kunci pencarian. Klaim baru dibuat oleh koder."
            />
          ) : (
            <div className="space-y-3">
              <div className="overflow-x-auto rounded-3xl border border-line bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Episode</TableHead>
                      <TableHead>Pseudonim</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Tinjauan terbuka</TableHead>
                      <TableHead className="text-right">Kode</TableHead>
                      <TableHead>Diperbarui</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((claim) => (
                      <TableRow key={claim.id}>
                        <TableCell className="font-medium">
                          <Link
                            href={`/klaim/${claim.id}`}
                            className="text-brand underline-offset-4 hover:underline"
                          >
                            {claim.episode_no}
                          </Link>
                          <span className="ml-1.5 text-xs text-muted-foreground">v{claim.version}</span>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{claim.patient_pseudonym}</TableCell>
                        <TableCell>
                          <StatusBadge kind="claim" value={claim.status} />
                        </TableCell>
                        <TableCell>
                          {claim.open_review_count > 0 ? (
                            <span className="inline-flex items-center gap-1.5">
                              <TierBadge tier={claim.highest_open_tier} compact />
                              <span className="text-xs text-muted-foreground">
                                {claim.open_review_count} butir
                              </span>
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground">Tidak ada</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{claim.code_count}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatDateTime(claim.updated_at)}
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
  );
}

"use client";

import { ScrollTextIcon, ShieldCheckIcon } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorNotice } from "@/components/shared/error-notice";
import { PageHeader } from "@/components/shared/page-header";
import { PaginationBar } from "@/components/shared/pagination-bar";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAction } from "@/hooks/use-action";
import { useApi } from "@/hooks/use-api";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { apiFetch, toQuery } from "@/lib/api";
import type { AuditEntry, ChainVerification, Page } from "@/lib/api-types";
import { formatDateTime, shortId } from "@/lib/format";

import { QueryBoundary } from "../shared/query-boundary";
import { RequirePermission } from "../shared/require-permission";

const PAGE_SIZE = 25;

function ChainResult({ result }: { result: ChainVerification }) {
  return result.valid ? (
    <Alert variant="success">
      <ShieldCheckIcon aria-hidden="true" />
      <AlertTitle>Rantai hash utuh</AlertTitle>
      <AlertDescription>{result.checked} catatan diperiksa; tidak ada perubahan atau penghapusan terdeteksi.</AlertDescription>
    </Alert>
  ) : (
    <Alert variant="destructive">
      <ShieldCheckIcon aria-hidden="true" />
      <AlertTitle>Rantai hash tidak konsisten</AlertTitle>
      <AlertDescription>
        Ketidaksesuaian pertama pada urutan {result.first_invalid_seq}: {result.reason}.
      </AlertDescription>
    </Alert>
  );
}

export function AuditView() {
  const [eventType, setEventType] = useState("");
  const [entityType, setEntityType] = useState("");
  const [page, setPage] = useState(1);
  const event = useDebouncedValue(eventType.trim());
  const entity = useDebouncedValue(entityType.trim());
  const log = useApi<Page<AuditEntry>>(
    `/v1/audit-log${toQuery({ event_type: event, entity_type: entity, page, page_size: PAGE_SIZE })}`,
  );
  const verify = useAction(() => apiFetch<ChainVerification>("/v1/audit-log/verify"));
  const [result, setResult] = useState<ChainVerification | null>(null);

  const runVerify = async () => {
    setResult(null);
    const outcome = await verify.run();
    if (outcome) setResult(outcome);
  };

  return (
    <RequirePermission permission="audit:read">
      <div className="space-y-6">
        <PageHeader
          title="Log audit"
          description="Catatan append-only untuk peristiwa penting. Setiap catatan menautkan hash catatan sebelumnya sehingga perubahan atau penghapusan dapat dideteksi."
          actions={
            <Button variant="outline" size="sm" onClick={() => void runVerify()} disabled={verify.pending}>
              <ShieldCheckIcon aria-hidden="true" />
              {verify.pending ? "Memeriksa..." : "Verifikasi rantai hash"}
            </Button>
          }
        />
        {result ? <ChainResult result={result} /> : null}
        <ErrorNotice error={verify.error} title="Verifikasi gagal dijalankan" />

        <div className="grid gap-3 rounded-3xl border border-line bg-white p-4 sm:grid-cols-2">
          <Input
            aria-label="Filter jenis peristiwa"
            placeholder="Jenis peristiwa, mis. review.verdict_recorded"
            value={eventType}
            onChange={(e) => {
              setEventType(e.target.value);
              setPage(1);
            }}
          />
          <Input
            aria-label="Filter jenis entitas"
            placeholder="Jenis entitas, mis. intervention"
            value={entityType}
            onChange={(e) => {
              setEntityType(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <QueryBoundary state={log} rows={6}>
          {(data) =>
            data.items.length === 0 ? (
              <EmptyState icon={ScrollTextIcon} title="Tidak ada catatan audit yang cocok" />
            ) : (
              <div className="space-y-3">
                <div className="overflow-x-auto rounded-3xl border border-line bg-white">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-right">Seq</TableHead>
                        <TableHead>Waktu</TableHead>
                        <TableHead>Peristiwa</TableHead>
                        <TableHead>Entitas</TableHead>
                        <TableHead>Aktor</TableHead>
                        <TableHead>Hash</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.items.map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell className="text-right tabular-nums">{entry.seq}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{formatDateTime(entry.created_at)}</TableCell>
                          <TableCell className="align-top">
                            <p className="font-mono text-xs font-medium text-ink">{entry.event_type}</p>
                            <details className="mt-1">
                              <summary className="cursor-pointer text-xs text-muted-foreground">Muatan</summary>
                              <pre className="mt-1 max-w-md overflow-x-auto rounded-xl bg-surface p-2 text-xs whitespace-pre-wrap">
                                {JSON.stringify(entry.payload, null, 2)}
                              </pre>
                            </details>
                          </TableCell>
                          <TableCell className="text-xs">
                            {entry.entity_type}
                            <span className="ml-1 font-mono text-muted-foreground">{shortId(entry.entity_id)}</span>
                          </TableCell>
                          <TableCell className="text-xs">
                            {entry.actor_type}
                            {entry.actor_id ? (
                              <span className="ml-1 font-mono text-muted-foreground">{shortId(entry.actor_id)}</span>
                            ) : null}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-muted-foreground" title={entry.record_hash}>
                            {shortId(entry.record_hash)}
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

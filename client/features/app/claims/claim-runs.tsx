import Link from "next/link";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RunSummary } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

import { VECTOR_LABELS, labelOf } from "../shared/labels";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";

type ClaimRunsProps = {
  runs: RunSummary[];
};

function RunTable({ runs }: ClaimRunsProps) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Vektor</TableHead>
            <TableHead>Aturan</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Hasil</TableHead>
            <TableHead>Tier</TableHead>
            <TableHead>Dimulai</TableHead>
            <TableHead className="text-right">Rincian</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => (
            <TableRow key={run.id}>
              <TableCell className="font-medium">{labelOf(VECTOR_LABELS, run.vector_code)}</TableCell>
              <TableCell className="text-xs">{run.rule_version}</TableCell>
              <TableCell>
                <StatusBadge kind="run" value={run.status} />
              </TableCell>
              <TableCell>
                <div className="space-y-1">
                  <StatusBadge kind="outcome" value={run.outcome} />
                  {run.abstain_reason ? (
                    <p className="max-w-xs text-xs whitespace-normal text-muted-foreground">
                      {run.abstain_reason}
                    </p>
                  ) : null}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(run.tier_counts).length === 0 ? (
                    <span className="text-xs text-muted-foreground">-</span>
                  ) : (
                    Object.entries(run.tier_counts)
                      .sort(([a], [b]) => b.localeCompare(a))
                      .map(([tier, count]) => (
                        <span key={tier} className="inline-flex items-center gap-1">
                          <TierBadge tier={tier} compact />
                          <span className="text-xs text-muted-foreground">×{count}</span>
                        </span>
                      ))
                  )}
                </div>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{formatDateTime(run.started_at)}</TableCell>
              <TableCell className="text-right">
                <Link href={`/pemeriksaan/${run.id}`} className="text-sm text-brand underline-offset-4 hover:underline">
                  Buka
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function ClaimRuns({ runs }: ClaimRunsProps) {
  const current = runs.filter((run) => !run.stale);
  const history = runs.filter((run) => run.stale);
  if (runs.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-line px-4 py-6 text-center text-sm text-muted-foreground">
        Belum ada hasil pemeriksaan. Pemeriksaan berjalan setelah coding dikirim.
      </p>
    );
  }
  return (
    <div className="space-y-4">
      {current.length > 0 ? (
        <RunTable runs={current} />
      ) : (
        <p className="text-sm text-muted-foreground">
          Tidak ada hasil yang berlaku untuk versi klaim ini. Kirim coding atau minta pemeriksaan ulang.
        </p>
      )}
      {history.length > 0 ? (
        <details className="rounded-2xl border border-line bg-surface p-3">
          <summary className="cursor-pointer text-sm font-medium text-ink">
            Riwayat hasil yang tidak berlaku ({history.length})
          </summary>
          <div className="mt-3">
            <RunTable runs={history} />
          </div>
        </details>
      ) : null}
    </div>
  );
}

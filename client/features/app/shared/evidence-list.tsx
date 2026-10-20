import { ShieldAlertIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Evidence } from "@/lib/api-types";
import { formatDateTime, shortId } from "@/lib/format";

import { EVIDENCE_KIND_LABELS, labelOf } from "./labels";

type EvidenceListProps = {
  items: Evidence[];
  highlightIds?: ReadonlySet<string>;
  emptyText?: string;
};

export function EvidenceList({ items, highlightIds, emptyText }: EvidenceListProps) {
  if (items.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-line px-4 py-6 text-center text-sm text-muted-foreground">
        {emptyText ?? "Belum ada bukti yang tercatat untuk klaim ini."}
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const cited = highlightIds?.has(item.id) ?? false;
        return (
          <li
            key={item.id}
            id={`bukti-${item.id}`}
            className={
              cited
                ? "rounded-2xl border border-brand/40 bg-lavender/40 p-4"
                : "rounded-2xl border border-line bg-surface p-4"
            }
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant="neutral">{labelOf(EVIDENCE_KIND_LABELS, item.kind)}</Badge>
              <Badge variant={item.assertion === "negates" ? "danger" : "success"}>
                {item.assertion === "negates" ? "Menafikan kode" : "Mendukung kode"}
              </Badge>
              {item.injection_suspected ? (
                <Badge variant="warning">
                  <ShieldAlertIcon aria-hidden="true" />
                  Dikarantina: dugaan instruksi tersisip
                </Badge>
              ) : null}
              {cited ? <Badge variant="brand">Dikutip pada temuan</Badge> : null}
              <span className="text-muted-foreground">
                {item.source_ref} ({item.source_type}) · {formatDateTime(item.recorded_at)}
              </span>
              <span className="font-mono text-muted-foreground" title={item.content_hash}>
                hash {shortId(item.content_hash)}
              </span>
            </div>
            {item.content_text !== null ? (
              <p className="mt-2 text-sm whitespace-pre-wrap text-ink">{item.content_text}</p>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                Isi bukti tidak ditampilkan untuk peran Anda.
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

import { Badge } from "@/components/ui/badge";

import { EVIDENCE_KIND_LABELS, labelOf } from "../shared/labels";

type Requirement = {
  id: string;
  label: string;
  evidence_kinds?: string[];
  keywords_any?: string[];
  source_types?: string[];
  min_count?: number;
  window?: string;
  window_grace_hours?: number;
};

type Spec = {
  check?: string;
  requirements?: Requirement[];
  conflicts_with_codes?: string[];
  anchor_kinds?: string[];
  note?: string | null;
};

const CHECK_LABELS: Record<string, string> = {
  evidence_presence: "Kehadiran bukti (phantom billing)",
  severity_support: "Dukungan keparahan (upcoding)",
  bundling_conflict: "Konflik kombinasi kode (unbundling)",
};

export function SpecView({ spec }: { spec: Record<string, unknown> }) {
  const typed = spec as Spec;
  const requirements = typed.requirements ?? [];
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="brand">{CHECK_LABELS[typed.check ?? ""] ?? typed.check}</Badge>
        {typed.note ? <span className="text-xs text-muted-foreground">{typed.note}</span> : null}
      </div>
      {typed.conflicts_with_codes && typed.conflicts_with_codes.length > 0 ? (
        <p>
          <span className="text-muted-foreground">Ditandai bila tercatat bersama: </span>
          <span className="font-mono text-xs">{typed.conflicts_with_codes.join(", ")}</span>
        </p>
      ) : null}
      {requirements.length > 0 ? (
        <ul className="space-y-2">
          {requirements.map((requirement) => (
            <li key={requirement.id} className="rounded-2xl bg-surface p-3">
              <p className="font-medium text-ink">{requirement.label}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                minimal {requirement.min_count ?? 1} bukti · jendela {requirement.window ?? "episode"}
                {requirement.window_grace_hours ? ` (+${requirement.window_grace_hours} jam)` : ""}
                {requirement.evidence_kinds?.length
                  ? ` · jenis: ${requirement.evidence_kinds.map((kind) => labelOf(EVIDENCE_KIND_LABELS, kind)).join(", ")}`
                  : ""}
                {requirement.source_types?.length ? ` · sumber: ${requirement.source_types.join(", ")}` : ""}
                {requirement.keywords_any?.length ? ` · kata kunci: ${requirement.keywords_any.join(", ")}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
      <details>
        <summary className="cursor-pointer text-xs text-muted-foreground">JSON spesifikasi</summary>
        <pre className="mt-1 overflow-x-auto rounded-xl bg-surface p-2 text-xs">{JSON.stringify(spec, null, 2)}</pre>
      </details>
    </div>
  );
}

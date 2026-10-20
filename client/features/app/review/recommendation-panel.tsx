import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Citation, InterventionDetail, Recommendation } from "@/lib/api-types";
import { formatPercent, shortId } from "@/lib/format";

import { CITATION_ROLE_LABELS, labelOf } from "../shared/labels";
import { StatusBadge } from "../shared/status-badge";
import { TierBadge } from "../shared/tier-badge";

function CitationItem({ citation }: { citation: Citation }) {
  const valid = citation.validation_status === "valid";
  return (
    <li className="rounded-2xl border border-line bg-surface p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge variant={valid ? "success" : "danger"}>{valid ? "Sitasi valid" : "Sitasi tidak valid"}</Badge>
        <span className="text-muted-foreground">{labelOf(CITATION_ROLE_LABELS, citation.role)}</span>
        <a href={`#bukti-${citation.evidence_item_id}`} className="font-mono text-brand underline-offset-4 hover:underline">
          bukti {shortId(citation.evidence_item_id)}
        </a>
        <span className="font-mono text-muted-foreground" title={citation.evidence_hash}>
          hash {shortId(citation.evidence_hash)}
        </span>
        {citation.start !== null && citation.end !== null ? (
          <span className="text-muted-foreground">
            rentang {citation.start}-{citation.end}
          </span>
        ) : null}
      </div>
      {citation.quote ? (
        <blockquote className="mt-2 border-l-2 border-brand/40 pl-3 text-ink">{citation.quote}</blockquote>
      ) : null}
      {citation.invalid_reason ? (
        <p className="mt-1 text-xs text-destructive">Alasan tidak valid: {citation.invalid_reason}</p>
      ) : null}
    </li>
  );
}

function ExpectedObserved({ recommendation }: { recommendation: Recommendation }) {
  const expected = recommendation.delta.expected ?? [];
  const observed = recommendation.delta.observed ?? [];
  if (expected.length === 0) return null;
  const byId = new Map(observed.map((item) => [item.requirement_id, item]));
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-ink">Expected evidence dan observed evidence</h3>
      <div className="overflow-x-auto rounded-2xl border border-line">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Persyaratan bukti</TableHead>
              <TableHead className="text-right">Minimal</TableHead>
              <TableHead className="text-right">Ditemukan</TableHead>
              <TableHead className="text-right">Di luar periode</TableHead>
              <TableHead>Hasil</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {expected.map((requirement) => {
              const match = byId.get(requirement.requirement_id);
              const found = match?.supporting_evidence_ids.length ?? 0;
              return (
                <TableRow key={requirement.requirement_id}>
                  <TableCell className="whitespace-normal">{requirement.label}</TableCell>
                  <TableCell className="text-right tabular-nums">{requirement.min_count}</TableCell>
                  <TableCell className="text-right tabular-nums">{found}</TableCell>
                  <TableCell className="text-right tabular-nums">{match?.out_of_window_evidence_ids.length ?? 0}</TableCell>
                  <TableCell>
                    <Badge variant={match?.satisfied ? "success" : "warning"}>
                      {match?.satisfied ? "Terpenuhi" : "Belum terpenuhi"}
                    </Badge>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-sm font-semibold text-ink">{title}</h3>
      <ul className="list-disc space-y-1 pl-5 text-sm text-ink/90">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function RecommendationPanel({ detail }: { detail: InterventionDetail }) {
  const recommendation = detail.recommendation;
  if (!recommendation) return null;
  const delta = recommendation.delta;
  const description = recommendation.mismatch_desc ?? recommendation.abstain_reason;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <TierBadge tier={detail.tier} />
        <Badge variant="neutral">Aturan kebijakan: {recommendation.policy_rule}</Badge>
        {recommendation.finding_status ? (
          <Badge variant={recommendation.finding_status === "valid" ? "success" : "warning"}>
            Temuan {recommendation.finding_status === "valid" ? "valid" : "diturunkan"}
          </Badge>
        ) : null}
        <StatusBadge kind="validation" value={detail.run.rule_validation_status} />
      </div>

      {description ? <p className="text-base text-ink">{description}</p> : null}

      {detail.run.rule_validation_status !== "tervalidasi_pakar" ? (
        <Alert variant="warning">
          <AlertTitle>Aturan belum divalidasi pakar</AlertTitle>
          <AlertDescription>
            Aturan expected evidence yang dipakai belum disetujui pakar casemix/RMIK sehingga hasil ini
            tidak boleh menjadi satu-satunya dasar kesimpulan.
          </AlertDescription>
        </Alert>
      ) : null}

      {recommendation.signal_strength !== null ? (
        <p className="rounded-2xl bg-surface px-4 py-3 text-sm">
          <span className="font-medium text-ink">Kekuatan sinyal: {formatPercent(recommendation.signal_strength)}</span>
          <span className="block text-xs text-muted-foreground">
            Rasio persyaratan bukti yang belum terpenuhi. Ini bukan probabilitas bahwa temuan benar dan bukan
            skor risiko terkalibrasi.
          </span>
        </p>
      ) : null}

      <ExpectedObserved recommendation={recommendation} />

      {delta.conflicting_codes && delta.conflicting_codes.length > 0 ? (
        <ListBlock title="Kode yang tercatat bersamaan" items={delta.conflicting_codes} />
      ) : null}

      {recommendation.citations.length > 0 ? (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-ink">Sitasi bukti</h3>
          <ul className="space-y-2">
            {recommendation.citations.map((citation) => (
              <CitationItem key={`${citation.evidence_item_id}-${citation.start ?? 0}`} citation={citation} />
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Tidak ada sitasi bukti pada butir ini.</p>
      )}

      <ListBlock title="Keterbatasan" items={delta.limitations ?? []} />
      <ListBlock title="Celah cakupan sumber" items={delta.coverage_gaps ?? []} />
      <ListBlock title="Penyesuaian Safety Governor" items={delta.governor_reasons ?? []} />
      <ListBlock
        title="Saran tindakan (bantuan, bukan perintah)"
        items={(delta.proposed_actions ?? []).map((action) => action.label)}
      />
    </div>
  );
}

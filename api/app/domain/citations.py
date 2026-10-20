import uuid
from dataclasses import dataclass
from typing import Literal

from app.domain.comparator import Comparison, EvidenceView
from app.domain.hashing import content_hash

QUOTE_MAX_CHARS = 280
FALLBACK_ANCHOR_LIMIT = 3

CitationRole = Literal["contradicts_claim", "examined_document"]


@dataclass(frozen=True)
class CandidateCitation:
    evidence_item_id: uuid.UUID
    evidence_hash: str
    start: int
    end: int
    quote: str
    role: CitationRole


@dataclass(frozen=True)
class EvidenceRecord:
    id: uuid.UUID
    faskes_id: uuid.UUID
    claim_id: uuid.UUID
    content_text: str
    content_hash: str


@dataclass(frozen=True)
class CitationVerdict:
    citation: CandidateCitation
    valid: bool
    reason: str | None


def _span(text: str) -> tuple[int, int, str]:
    end = min(len(text), QUOTE_MAX_CHARS)
    return 0, end, text[:end]


def _keyword_span(text: str, keywords: list[str]) -> tuple[int, int, str]:
    lowered = text.lower()
    for keyword in keywords:
        position = lowered.find(keyword.lower())
        if position >= 0:
            start = max(0, position - 40)
            end = min(len(text), position + len(keyword) + 120)
            return start, end, text[start:end]
    return _span(text)


def build_candidates(
    comparison: Comparison, evidence: list[EvidenceView]
) -> list[CandidateCitation]:
    by_id = {e.id: e for e in evidence if not e.quarantined}
    candidates: list[CandidateCitation] = []
    seen: set[uuid.UUID] = set()

    for outcome in comparison.unmet:
        for evidence_id in outcome.negating_ids:
            item = by_id.get(evidence_id)
            if item is None or item.id in seen:
                continue
            start, end, quote = _keyword_span(item.text, outcome.requirement.keywords_any)
            candidates.append(
                CandidateCitation(item.id, item.content_hash, start, end, quote, "contradicts_claim")
            )
            seen.add(item.id)

    if candidates:
        return candidates

    anchors = [
        e
        for e in by_id.values()
        if e.kind in comparison.rule.spec.anchor_kinds and e.text
    ]
    if not anchors:
        relevant_types = {
            t for o in comparison.unmet for t in o.requirement.source_types
        }
        pool = [
            e
            for e in by_id.values()
            if e.text and (not relevant_types or e.source_type in relevant_types)
        ]
        anchors = sorted(pool, key=lambda e: e.recorded_at, reverse=True)[:FALLBACK_ANCHOR_LIMIT]
    for item in sorted(anchors, key=lambda e: e.recorded_at):
        if item.id in seen:
            continue
        start, end, quote = _span(item.text)
        candidates.append(
            CandidateCitation(item.id, item.content_hash, start, end, quote, "examined_document")
        )
        seen.add(item.id)
    return candidates


def validate_citations(
    candidates: list[CandidateCitation],
    records: dict[uuid.UUID, EvidenceRecord],
    *,
    faskes_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> list[CitationVerdict]:
    verdicts: list[CitationVerdict] = []
    for candidate in candidates:
        record = records.get(candidate.evidence_item_id)
        reason: str | None = None
        if record is None:
            reason = "bukti tidak ditemukan"
        elif record.faskes_id != faskes_id:
            reason = "bukti berasal dari faskes lain"
        elif record.claim_id != claim_id:
            reason = "bukti bukan milik klaim ini"
        elif record.content_hash != candidate.evidence_hash:
            reason = "hash bukti tidak cocok dengan hash yang dikutip"
        elif content_hash(record.content_text) != record.content_hash:
            reason = "isi bukti tidak cocok dengan hash tersimpan"
        elif not 0 <= candidate.start < candidate.end <= len(record.content_text):
            reason = "rentang kutipan di luar isi bukti"
        elif record.content_text[candidate.start : candidate.end] != candidate.quote:
            reason = "teks kutipan tidak sama dengan isi bukti"
        verdicts.append(CitationVerdict(candidate, reason is None, reason))
    return verdicts

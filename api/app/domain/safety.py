import re
from dataclasses import dataclass, field

from app.domain.enums import RuleValidation, Tier

FORBIDDEN_LANGUAGE: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bfraud\b",
        r"\bpenipuan\b",
        r"\bkecurangan\b",
        r"\bcurang\b",
        r"\bmenipu\b",
        r"\bfiktif\b",
        r"\bkorupsi\b",
        r"\bsanksi\b",
        r"\bpidana\b",
        r"klaim\s+(akan\s+)?ditolak",
        r"menolak\s+klaim",
        r"tolak\s+klaim",
    )
)

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)?\s*(instructions?|prompts?|rules?)",
        r"abaikan\s+(semua\s+|seluruh\s+)?(instruksi|perintah|aturan)",
        r"\b(system|developer)\s+prompt\b",
        r"\byou\s+are\s+now\b",
        r"\b(kamu|anda)\s+(sekarang|adalah)\b",
        r"(disregard|override)\s+(the\s+)?(policy|rules?|kebijakan)",
        r"(set|ubah|ganti|naikkan|turunkan)\s+(tier|policy|kebijakan)",
        r"(kirim|ekspor|export|exfiltrate|send|forward)\b.{0,40}\b(data|database|semua|pasien|password|token|rahasia)",
        r"<\s*/?\s*(system|assistant|tool|instruction)s?\s*>",
        r"\b(tool_call|function_call)\b",
        r"setujui\s+(klaim|semua)",
    )
)

SAFE_FALLBACK_DESCRIPTION = (
    "Ditemukan ketidaksesuaian antara kode klaim dan bukti yang tersedia. "
    "Diperlukan pemeriksaan oleh verifikator."
)


def forbidden_language(text: str) -> list[str]:
    return [p.pattern for p in FORBIDDEN_LANGUAGE if p.search(text)]


def looks_like_injection(text: str) -> bool:
    return any(p.search(text) for p in INJECTION_PATTERNS)


def sanitize_description(text: str) -> tuple[str, list[str]]:
    flags = forbidden_language(text)
    if flags:
        return SAFE_FALLBACK_DESCRIPTION, flags
    return text, []


@dataclass(frozen=True)
class GovernorVerdict:
    tier: Tier
    overridden: bool
    reasons: list[str] = field(default_factory=list)


def govern(
    *,
    tier: Tier,
    rule_validation: str,
    citation_valid_count: int,
    coverage_adequate: bool,
    unresolved_conflict: bool,
) -> GovernorVerdict:
    if tier in (Tier.T2, Tier.T3):
        if citation_valid_count < 1:
            return GovernorVerdict(Tier.T0, True, ["sitasi bukti valid tidak tersedia"])
        if not coverage_adequate:
            return GovernorVerdict(Tier.T0, True, ["cakupan sumber bukti tidak memadai"])
        if unresolved_conflict:
            return GovernorVerdict(Tier.T0, True, ["bukti saling bertentangan belum terselesaikan"])
        if rule_validation == RuleValidation.UNVALIDATED.value:
            return GovernorVerdict(
                Tier.T1,
                True,
                ["aturan belum divalidasi pakar sehingga tidak boleh menjadi dasar rekomendasi tinjauan"],
            )
    return GovernorVerdict(tier, False)

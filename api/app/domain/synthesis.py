from dataclasses import dataclass
from typing import Protocol

from app.domain.comparator import Comparison
from app.domain.enums import CheckType, RuleValidation
from app.domain.safety import SAFE_FALLBACK_DESCRIPTION, sanitize_description

MAX_DESCRIPTION_CHARS = 1000
DEFAULT_ACTION = "periksa_dokumentasi"

ALLOWED_ACTIONS: dict[str, str] = {
    "periksa_dokumentasi": "Periksa kelengkapan dokumentasi pelayanan di sumber bukti",
    "minta_klarifikasi_dpjp": "Minta klarifikasi kepada DPJP bila dokumentasi memang belum lengkap",
    "tinjau_kode": "Tinjau kembali kode yang dipilih bersama koder",
    "lengkapi_bukti": "Lengkapi atau sinkronkan bukti yang belum tercatat lalu jalankan pemeriksaan ulang",
}

PRESENCE_LIMITATION = (
    "Bukti yang tidak ditemukan tidak membuktikan bahwa pelayanan tidak pernah dilakukan."
)
UNVALIDATED_LIMITATION = (
    "Aturan yang dipakai belum divalidasi pakar casemix/RMIK."
)
SIMULATION_LIMITATION = (
    "Aturan yang dipakai adalah aturan simulasi, bukan aturan klinis resmi."
)
NON_PROBABILITY_NOTE = (
    "signal_strength adalah rasio persyaratan bukti yang belum terpenuhi, bukan probabilitas."
)


@dataclass(frozen=True)
class SynthesizedFinding:
    mismatch_desc: str
    proposed_actions: list[str]
    limitations: list[str]
    safety_flags: list[str]


class Synthesizer(Protocol):
    def synthesize(self, comparison: Comparison) -> SynthesizedFinding: ...


def _labels(comparison: Comparison) -> str:
    return "; ".join(o.requirement.label for o in comparison.unmet)


def required_limitations(comparison: Comparison) -> list[str]:
    limitations: list[str] = []
    if comparison.check is not CheckType.BUNDLING_CONFLICT:
        limitations.append(PRESENCE_LIMITATION)
    if comparison.rule.validation_status == RuleValidation.UNVALIDATED.value:
        limitations.append(UNVALIDATED_LIMITATION)
    elif comparison.rule.validation_status == RuleValidation.SIMULATION.value:
        limitations.append(SIMULATION_LIMITATION)
    limitations.append(NON_PROBABILITY_NOTE)
    return limitations


def enforce_output_policy(
    comparison: Comparison, output: SynthesizedFinding
) -> SynthesizedFinding:
    flags = list(output.safety_flags)

    description = output.mismatch_desc.strip()[:MAX_DESCRIPTION_CHARS]
    if description:
        description, found = sanitize_description(description)
        flags.extend(found)
    else:
        description = SAFE_FALLBACK_DESCRIPTION

    actions: list[str] = []
    for action in output.proposed_actions:
        if action not in ALLOWED_ACTIONS:
            flags.append(f"aksi_tidak_diizinkan:{action}")
        elif action not in actions:
            actions.append(action)
    if not actions:
        actions.append(DEFAULT_ACTION)

    limitations: list[str] = []
    for item in output.limitations:
        cleaned, found = sanitize_description(item.strip())
        if found:
            flags.extend(found)
        elif cleaned and cleaned not in limitations:
            limitations.append(cleaned)
    for required in required_limitations(comparison):
        if required not in limitations:
            limitations.append(required)

    return SynthesizedFinding(description, actions, limitations, list(dict.fromkeys(flags)))


class TemplateSynthesizer:
    def synthesize(self, comparison: Comparison) -> SynthesizedFinding:
        code = comparison.code.code
        check = comparison.check
        has_contradiction = any(o.negating_ids for o in comparison.unmet)

        if check is CheckType.BUNDLING_CONFLICT:
            others = ", ".join(c.code for c in comparison.conflicting_codes)
            description = (
                f"Kode {code} tercatat bersamaan dengan {others}. Kombinasi ini ditandai oleh "
                "aturan pengelompokan yang berlaku dan perlu diperiksa apakah penggabungan kode sudah sesuai."
            )
            actions = ["tinjau_kode", "periksa_dokumentasi"]
        elif has_contradiction:
            description = (
                f"Terdapat bukti yang bertentangan dengan kode {code} untuk persyaratan: "
                f"{_labels(comparison)}. Diperlukan pemeriksaan oleh verifikator."
            )
            actions = ["periksa_dokumentasi", "minta_klarifikasi_dpjp"]
        elif check is CheckType.SEVERITY_SUPPORT:
            description = (
                f"Bukti pendukung tingkat keparahan untuk kode {code} belum ditemukan pada sumber "
                f"yang diperiksa: {_labels(comparison)}."
            )
            actions = ["periksa_dokumentasi", "tinjau_kode", "minta_klarifikasi_dpjp"]
        else:
            description = (
                f"Bukti yang diharapkan untuk kode {code} belum ditemukan pada sumber yang "
                f"diperiksa: {_labels(comparison)}."
            )
            actions = ["periksa_dokumentasi", "lengkapi_bukti", "minta_klarifikasi_dpjp"]

        safe_description, flags = sanitize_description(description)
        return SynthesizedFinding(safe_description, actions, required_limitations(comparison), flags)

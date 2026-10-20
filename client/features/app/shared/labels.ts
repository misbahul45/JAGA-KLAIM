export type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "brand";

export type Labelled = { label: string; tone: Tone };

export type StatusKind =
  | "claim"
  | "job"
  | "run"
  | "outcome"
  | "health"
  | "version"
  | "update"
  | "validation";

export const STATUS_TABLES: Record<StatusKind, Record<string, Labelled>> = {
  claim: {
    draft: { label: "Draf", tone: "neutral" },
    coding_submitted: { label: "Menunggu pemeriksaan", tone: "info" },
    under_review: { label: "Dalam tinjauan", tone: "warning" },
    needs_clarification: { label: "Perlu klarifikasi", tone: "warning" },
    returned_to_coder: { label: "Dikembalikan ke koder", tone: "danger" },
    ready_to_lock: { label: "Siap dikunci", tone: "success" },
    locked: { label: "Dikunci", tone: "brand" },
  },
  job: {
    queued: { label: "Mengantre", tone: "neutral" },
    processing: { label: "Diproses", tone: "info" },
    succeeded: { label: "Selesai", tone: "success" },
    partial: { label: "Selesai sebagian", tone: "warning" },
    failed: { label: "Gagal", tone: "danger" },
    cancelled: { label: "Dibatalkan", tone: "neutral" },
    stale: { label: "Tidak berlaku", tone: "neutral" },
  },
  run: {
    running: { label: "Berjalan", tone: "info" },
    succeeded: { label: "Selesai", tone: "success" },
    partial: { label: "Sebagian (ada abstain)", tone: "warning" },
    failed: { label: "Gagal", tone: "danger" },
    cancelled: { label: "Dibatalkan", tone: "neutral" },
  },
  outcome: {
    no_action: { label: "No Action", tone: "success" },
    findings: { label: "Ada ketidaksesuaian", tone: "warning" },
    abstained: { label: "Abstain", tone: "neutral" },
  },
  health: {
    unknown: { label: "Belum diketahui", tone: "neutral" },
    healthy: { label: "Sehat", tone: "success" },
    degraded: { label: "Terganggu", tone: "warning" },
    down: { label: "Tidak tersedia", tone: "danger" },
  },
  version: {
    draft: { label: "Draf", tone: "neutral" },
    pending_approval: { label: "Menunggu persetujuan", tone: "warning" },
    approved: { label: "Disetujui", tone: "info" },
    active: { label: "Aktif", tone: "success" },
    retired: { label: "Dipensiunkan", tone: "neutral" },
    rejected: { label: "Ditolak", tone: "danger" },
  },
  update: {
    proposed: { label: "Diusulkan", tone: "neutral" },
    evaluating: { label: "Dievaluasi", tone: "info" },
    evaluated: { label: "Selesai dievaluasi", tone: "info" },
    approved: { label: "Disetujui", tone: "success" },
    rejected: { label: "Ditolak", tone: "danger" },
    activated: { label: "Diaktifkan", tone: "brand" },
    rolled_back: { label: "Di-rollback", tone: "neutral" },
  },
  validation: {
    belum_tervalidasi: { label: "Belum tervalidasi pakar", tone: "warning" },
    simulasi: { label: "Aturan simulasi", tone: "info" },
    tervalidasi_pakar: { label: "Tervalidasi pakar", tone: "success" },
  },
};

export const VECTOR_LABELS: Record<string, string> = {
  phantom_billing: "Phantom billing",
  upcoding: "Upcoding",
  unbundling: "Unbundling",
};

export const VERDICT_LABELS: Record<string, string> = {
  supports_finding: "Temuan didukung bukti",
  does_not_support_finding: "Temuan tidak didukung bukti",
  needs_clarification: "Perlu klarifikasi",
  insufficient_evidence: "Bukti belum cukup",
};

export const FOLLOW_UP_LABELS: Record<string, string> = {
  proceed: "Lanjutkan proses",
  return_to_coder: "Kembalikan ke koder",
  request_clarification: "Minta klarifikasi DPJP",
};

export const ROLE_LABELS: Record<string, string> = {
  coder: "Koder",
  verifier: "Verifikator internal",
  faskes_admin: "Admin faskes",
  auditor: "Auditor",
  rule_admin: "Pengelola aturan",
  rule_approver: "Penyetuju aturan",
};

export const EVIDENCE_KIND_LABELS: Record<string, string> = {
  resume_medis: "Resume medis",
  catatan_tindakan: "Catatan tindakan",
  pemberian_obat: "Pemberian obat",
  hasil_lab: "Hasil laboratorium",
  hasil_radiologi: "Hasil radiologi",
  catatan_keperawatan: "Catatan keperawatan",
  lainnya: "Lainnya",
};

export const CODE_TYPE_LABELS: Record<string, string> = {
  diagnosis: "Diagnosis",
  procedure: "Prosedur",
  inacbg: "INA-CBG",
  other: "Lainnya",
};

export const CITATION_ROLE_LABELS: Record<string, string> = {
  contradicts_claim: "Bukti yang bertentangan dengan kode",
  examined_document: "Dokumen yang diperiksa",
};

export const STEP_LABELS: Record<string, string> = {
  context_build: "Menyusun konteks klaim dan aturan",
  source_check: "Memeriksa kesehatan sumber bukti",
  retrieval: "Mengambil bukti klaim",
  compare: "Membandingkan expected dan observed evidence",
  validate_citations: "Memvalidasi sitasi bukti",
  policy_decide: "Menetapkan tier dengan policy engine",
  safety_check: "Pemeriksaan Safety Governor",
  synthesize: "Menyusun uraian ketidaksesuaian",
};

export const EVENT_LABELS: Record<string, string> = {
  "coding.submitted": "Pengiriman coding",
  "manual.rerun": "Pemeriksaan ulang manual",
};

export function labelOf(table: Record<string, string>, key: string | null | undefined): string {
  if (!key) return "-";
  return table[key] ?? key;
}

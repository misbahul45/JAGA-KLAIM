export const EVIDENCE_TERMS: { term: string; text: string }[] = [
  {
    term: "Expected evidence",
    text: "Bukti yang diharapkan sesuai aturan.",
  },
  {
    term: "Observed evidence",
    text: "Bukti yang ditemukan dari sumber.",
  },
  {
    term: "Delta comparison",
    text: "Selisih antara bukti yang diharapkan dan ditemukan.",
  },
  {
    term: "Evidence citation",
    text: "Rujukan sumber untuk mendukung temuan.",
  },
  {
    term: "Investigation timeline",
    text: "Urutan langkah pemeriksaan oleh agen.",
  },
];

export const TIMELINE_STEPS: string[] = [
  "Memuat aturan dan bukti yang dibutuhkan.",
  "Mencari bukti dari sumber yang diizinkan.",
  "Menelusuri sumber dengan tool yang tersedia.",
  "Membandingkan bukti yang dibutuhkan dan ditemukan.",
  "Menyajikan temuan beserta rujukannya.",
];

export const AUTHORITY_POINTS: string[] = [
  "Koder dan verifikator dapat menelusuri dasar setiap temuan.",
  "Verifikator menilai secara mandiri sebelum rekomendasi T2 dan T3 dibuka.",
  "Verifikator dapat menerima, menolak, atau mengeskalasi temuan.",
  "Setiap keputusan disertai alasan dan tercatat dalam audit trail.",
];

export const AUTHORITY_FLOW: string[] = [
  "Penilaian mandiri",
  "Rekomendasi dibuka",
  "Keputusan beralasan",
  "Audit trail",
];

export const AI_LIMITS: string[] = [
  "AI tidak menetapkan fraud sebagai fakta.",
  "AI tidak menolak klaim secara otomatis.",
  "AI tidak mengubah kode tanpa persetujuan manusia.",
  "Bukti yang tidak ditemukan bukan bukti bahwa pelayanan tidak dilakukan.",
];
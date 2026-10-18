export const EVIDENCE_TERMS: { term: string; text: string }[] = [
  {
    term: "Expected evidence",
    text: "Bukti yang seharusnya tersedia menurut aturan.",
  },
  {
    term: "Observed evidence",
    text: "Bukti yang benar-benar ditemukan.",
  },
  {
    term: "Delta comparison",
    text: "Perbandingan antara expected dan observed evidence.",
  },
  {
    term: "Evidence citation",
    text: "Referensi ke sumber yang mendukung temuan.",
  },
  {
    term: "Investigation timeline",
    text: "Langkah operasional yang dilakukan agen.",
  },
];

export const TIMELINE_STEPS: string[] = [
  "Mengambil expected evidence dari rule version aktif.",
  "Menelusuri sumber yang diizinkan melalui RAG.",
  "Memanggil tool pencarian yang diizinkan.",
  "Membandingkan expected dan observed evidence.",
  "Menyusun temuan dengan sitasi bukti.",
];

export const AUTHORITY_POINTS: string[] = [
  "Koder dan verifikator dapat memeriksa dasar temuan.",
  "Verifikator wajib memberikan penilaian mandiri sebelum rekomendasi T2 dan T3 dibuka.",
  "Verifikator dapat menerima, menolak, atau mengeskalasi temuan.",
  "Setiap verdict mempunyai alasan dan tercatat pada audit trail.",
];

export const AUTHORITY_FLOW: string[] = [
  "Penilaian mandiri",
  "Rekomendasi dibuka",
  "Verdict dengan alasan",
  "Audit trail",
];

export const AI_LIMITS: string[] = [
  "AI tidak menetapkan fraud sebagai fakta final.",
  "AI tidak menolak klaim secara otomatis.",
  "AI tidak mengubah kode klaim tanpa persetujuan manusia.",
  "Bukti yang tidak ditemukan tidak otomatis membuktikan bahwa pelayanan tidak pernah dilakukan.",
];

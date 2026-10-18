export type FaqItem = { question: string; answer: string };

export const FAQ_ITEMS: FaqItem[] = [
  {
    question: "Apa itu JAGA-KLAIM?",
    answer:
      "AI-powered pre-claim verification copilot untuk koder dan verifikator internal fasilitas kesehatan. JAGA-KLAIM memeriksa konsistensi coding dengan bukti klinis dan operasional sebelum klaim diajukan, lalu menyerahkan temuannya kepada manusia.",
  },
  {
    question: "Masalah apa yang diselesaikan?",
    answer:
      "Ketidaksesuaian antara kode dan bukti yang baru ditemukan pada tahap berikutnya, sehingga menimbulkan koreksi dan klarifikasi. Dokumentasi yang tersebar di banyak sumber juga sulit dibandingkan secara sistematis dengan bukti yang seharusnya ada.",
  },
  {
    question: "Siapa pengguna utamanya?",
    answer: "Koder dan verifikator internal fasilitas kesehatan.",
  },
  {
    question: "Kapan sistem digunakan dalam proses klaim?",
    answer:
      "Setelah coding dan grouping INA-CBG selesai, dan sebelum klaim diajukan.",
  },
  {
    question: "Bagaimana AI agent melakukan investigasi?",
    answer:
      "Agent menelusuri bukti dari sumber yang diizinkan melalui RAG dan tool yang diizinkan, mencatat setiap langkahnya pada investigation timeline, lalu menyusun temuan yang disertai sitasi bukti. Agent tidak menentukan status akhir klaim.",
  },
  {
    question: "Apa perbedaan expected evidence dan observed evidence?",
    answer:
      "Expected evidence adalah bukti yang seharusnya tersedia menurut rule version aktif. Observed evidence adalah bukti yang benar-benar ditemukan agent. Selisih keduanya disebut delta.",
  },
  {
    question: "Apa arti intervensi T0 sampai T3?",
    answer:
      "T0 Abstain: tidak ada intervensi karena bukti tidak memadai. T1 Inform: informasi tentang ketidaksesuaian ringan. T2 Recommend Review: rekomendasi pemeriksaan tambahan dengan penilaian mandiri yang wajib. T3 Flag for Human Verdict: temuan dan bukti disajikan untuk keputusan manusia.",
  },
  {
    question: "Apakah JAGA-KLAIM dapat menolak klaim secara otomatis?",
    answer:
      "Tidak. AI tidak menolak klaim secara otomatis, tidak menetapkan fraud sebagai fakta final, dan tidak mengubah kode klaim tanpa persetujuan manusia.",
  },
  {
    question: "Bagaimana keputusan manusia dan perubahan aturan diaudit?",
    answer:
      "Setiap verdict mempunyai alasan dan tercatat pada audit trail, bersama versi aturan dan tingkat intervensi yang berlaku. Verdict dapat menjadi dasar usulan perubahan aturan, yang membutuhkan persetujuan komite governance. Versi aturan sebelumnya tetap dapat ditinjau.",
  },
  {
    question: "Bagaimana sistem menangani privasi data?",
    answer:
      "Pemrosesan dilakukan dalam batas fasilitas kesehatan, akses dibatasi sesuai kewenangan, data pasien diminimalkan dan dipseudonimkan sesuai kebutuhan, dan hanya sumber yang diizinkan yang diakses. Penggunaan data riil harus memenuhi persyaratan legal, etis, dan pelindungan data yang relevan.",
  },
  {
    question: "Apakah JAGA-KLAIM sudah diuji di lingkungan rumah sakit?",
    answer:
      "Belum. JAGA-KLAIM masih pada tahap perancangan dan pengembangan awal. Halaman ini tidak menampilkan klaim akurasi, efisiensi, atau penghematan yang belum terbukti.",
  },
];

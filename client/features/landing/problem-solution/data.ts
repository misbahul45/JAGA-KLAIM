import {
  HistoryIcon,
  LayersIcon,
  ScaleIcon,
  TriangleAlertIcon,
  type LucideIcon,
} from "lucide-react";

export type ProblemItem = {
  icon: LucideIcon;
  title: string;
  text: string;
};

export const PROBLEMS: ProblemItem[] = [
  {
    icon: TriangleAlertIcon,
    title: "Kode belum didukung bukti yang memadai",
    text: "Kode diagnosis atau prosedur perlu diperiksa kesesuaiannya dengan dokumentasi klinis yang tersedia.",
  },
  {
    icon: LayersIcon,
    title: "Dokumentasi tersebar",
    text: "Informasi pendukung klaim dapat berada di berbagai dokumen dan sumber yang perlu ditinjau.",
  },
  {
    icon: ScaleIcon,
    title: "Kesesuaian bukti sulit diperiksa",
    text: "Bukti yang dibutuhkan perlu dibandingkan dengan bukti yang ditemukan agar kekurangan dapat diketahui.",
  },
  {
    icon: HistoryIcon,
    title: "Ketidaksesuaian terlambat diketahui",
    text: "Temuan pada tahap berikutnya dapat memerlukan klarifikasi dan koreksi tambahan.",
  },
];

export const SOLUTION_STEPS: string[] = [
  "Coding dan grouping INA-CBG diselesaikan oleh petugas.",
  "Sistem mengidentifikasi bukti yang dibutuhkan berdasarkan aturan yang digunakan.",
  "AI membantu menelusuri sumber bukti yang diizinkan.",
  "Sistem menyajikan perbandingan antara bukti yang dibutuhkan dan bukti yang ditemukan.",
  "Koder atau verifikator meninjau temuan dan menentukan tindak lanjut.",
];
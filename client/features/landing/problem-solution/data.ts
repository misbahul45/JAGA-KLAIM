import {
  HistoryIcon,
  LayersIcon,
  ScaleIcon,
  TriangleAlertIcon,
  type LucideIcon,
} from "lucide-react";

export type ProblemItem = { icon: LucideIcon; title: string; text: string };

export const PROBLEMS: ProblemItem[] = [
  {
    icon: TriangleAlertIcon,
    title: "Kode dan bukti tidak selaras",
    text: "Ketidaksesuaian antara kode diagnosis atau prosedur dan bukti yang tersedia.",
  },
  {
    icon: LayersIcon,
    title: "Bukti tersebar",
    text: "Dokumentasi klinis dan operasional tersebar di berbagai sumber.",
  },
  {
    icon: ScaleIcon,
    title: "Perbandingan tidak sistematis",
    text: "Sulit membandingkan bukti yang seharusnya ada dengan bukti aktual secara sistematis.",
  },
  {
    icon: HistoryIcon,
    title: "Ditemukan terlambat",
    text: "Koreksi dan klarifikasi dibutuhkan ketika ketidaksesuaian baru ditemukan pada tahap berikutnya.",
  },
];

export const SOLUTION_STEPS: string[] = [
  "Pemeriksaan dimulai setelah coding dan grouping INA-CBG selesai.",
  "Sistem menentukan expected evidence berdasarkan aturan yang berlaku.",
  "AI agent menelusuri evidence dari sumber yang diizinkan.",
  "Sistem membandingkan expected evidence dengan observed evidence.",
  "Hasil pemeriksaan disampaikan kepada koder atau verifikator untuk ditindaklanjuti.",
];

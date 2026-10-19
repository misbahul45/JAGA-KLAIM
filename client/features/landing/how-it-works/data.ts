import {
  BotIcon,
  ClipboardCheckIcon,
  GavelIcon,
  ListChecksIcon,
  ScaleIcon,
  ScrollTextIcon,
  UserCheckIcon,
  type LucideIcon,
} from "lucide-react";

export type Stage = {
  icon: LucideIcon;
  name: string;
  description: string;
};

export const STAGES: Stage[] = [
  {
    icon: ClipboardCheckIcon,
    name: "Input Klaim",
    description: "Menerima hasil coding dan grouping INA-CBG.",
  },
  {
    icon: ListChecksIcon,
    name: "Pemetaan Bukti",
    description: "Menentukan bukti yang dibutuhkan sesuai aturan aktif.",
  },
  {
    icon: BotIcon,
    name: "Investigasi AI",
    description: "Menelusuri bukti dari sumber yang diizinkan.",
  },
  {
    icon: ScaleIcon,
    name: "Analisis Bukti",
    description: "Membandingkan bukti yang dibutuhkan dan ditemukan.",
  },
  {
    icon: GavelIcon,
    name: "Mesin Kebijakan",
    description: "Menentukan tingkat intervensi berdasarkan aturan.",
  },
  {
    icon: UserCheckIcon,
    name: "Tinjauan Manusia",
    description: "Membantu koder dan verifikator menilai temuan.",
  },
  {
    icon: ScrollTextIcon,
    name: "Audit dan Evaluasi",
    description: "Mencatat proses untuk penelusuran dan evaluasi aturan.",
  },
];

export const PRINCIPLES: { title: string; text: string }[] = [
  {
    title: "Keputusan oleh manusia",
    text: "AI membantu menelusuri bukti. Keputusan akhir tetap berada pada manusia.",
  },
  {
    title: "Aturan terpisah dari AI",
    text: "Mesin kebijakan menentukan tingkat intervensi berdasarkan aturan.",
  },
  {
    title: "Temuan dapat ditelusuri",
    text: "Temuan dilengkapi rujukan ke sumber bukti yang mendukungnya.",
  },
  {
    title: "Semua hasil tercatat",
    text: "Hasil No Action tetap masuk audit trail saat tidak ditemukan perbedaan bukti.",
  },
];
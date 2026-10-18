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
    name: "Claim Input",
    description: "Menerima hasil coding dan grouping INA-CBG.",
  },
  {
    icon: ListChecksIcon,
    name: "Expected Evidence Engine",
    description: "Menentukan bukti yang diperlukan berdasarkan rule version aktif.",
  },
  {
    icon: BotIcon,
    name: "AI Investigation Agent",
    description: "Menelusuri bukti melalui RAG dan tool yang diizinkan.",
  },
  {
    icon: ScaleIcon,
    name: "Delta Analysis",
    description: "Membandingkan expected dan observed evidence.",
  },
  {
    icon: GavelIcon,
    name: "Deterministic Policy Engine",
    description: "Menetapkan tingkat intervensi berdasarkan aturan.",
  },
  {
    icon: UserCheckIcon,
    name: "Human Workspace",
    description: "Menyediakan temuan dan bukti untuk pemeriksaan manusia.",
  },
  {
    icon: ScrollTextIcon,
    name: "Audit & Governance",
    description:
      "Mencatat proses dan mendukung perbaikan aturan secara terkendali.",
  },
];

export const PRINCIPLES: { title: string; text: string }[] = [
  {
    title: "AI tidak menentukan status akhir klaim",
    text: "AI agent hanya menelusuri dan menyusun temuan. Status klaim tetap ditetapkan manusia.",
  },
  {
    title: "Policy engine terpisah dari AI",
    text: "Tingkat intervensi ditetapkan oleh aturan deterministik, bukan oleh proses investigasi AI.",
  },
  {
    title: "Temuan wajib bersitasi",
    text: "Setiap temuan didukung bukti yang dapat ditelusuri kembali ke sumbernya.",
  },
  {
    title: "Tanpa delta, tetap tercatat",
    text: "Bila tidak ditemukan delta, hasilnya No Action dan tetap masuk audit trail.",
  },
];

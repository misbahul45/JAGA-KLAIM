import {
  GhostIcon,
  SplitIcon,
  TrendingUpIcon,
  type LucideIcon,
} from "lucide-react";

export type RiskVector = {
  icon: LucideIcon;
  name: string;
  focus: string;
  surface: string;
};

export const RISK_VECTORS: RiskVector[] = [
  {
    icon: GhostIcon,
    name: "Phantom & Repeat Billing",
    focus:
      "Konsistensi klaim dengan bukti layanan dan kemungkinan pencatatan berulang.",
    surface: "bg-bento-lavender",
  },
  {
    icon: TrendingUpIcon,
    name: "Upcoding",
    focus:
      "Konsistensi kode diagnosis atau tindakan dengan bukti yang tersedia.",
    surface: "bg-bento-sun",
  },
  {
    icon: SplitIcon,
    name: "Unbundling",
    focus:
      "Konsistensi pemisahan atau pengelompokan kode berdasarkan aturan yang berlaku.",
    surface: "bg-bento-sky",
  },
];

export type Tier = {
  code: string;
  name: string;
  summary: string;
  detail: string;
  level: number;
  color: string;
};

export const TIERS: Tier[] = [
  {
    code: "T0",
    name: "Abstain",
    summary: "Tidak melakukan intervensi karena bukti tidak memadai.",
    detail: "Abstain adalah bagian dari desain sistem, bukan kegagalan.",
    level: 1,
    color: "bg-muted-foreground",
  },
  {
    code: "T1",
    name: "Inform",
    summary: "Memberikan informasi mengenai ketidaksesuaian ringan.",
    detail: "Tidak semua temuan harus menghasilkan alert yang mengganggu.",
    level: 2,
    color: "bg-info",
  },
  {
    code: "T2",
    name: "Recommend Review",
    summary:
      "Merekomendasikan pemeriksaan tambahan dan mewajibkan penilaian mandiri.",
    detail: "Verifikator memberikan penilaian mandiri sebelum rekomendasi dibuka.",
    level: 3,
    color: "bg-sun",
  },
  {
    code: "T3",
    name: "Flag for Human Verdict",
    summary: "Menyajikan temuan dan bukti untuk keputusan manusia.",
    detail:
      "Keputusan akhir ada pada verifikator: terima, tolak, atau eskalasi, dengan alasan yang tercatat.",
    level: 4,
    color: "bg-magenta",
  },
];

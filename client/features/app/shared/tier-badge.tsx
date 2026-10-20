import { CircleSlashIcon, EyeIcon, FlagIcon, InfoIcon, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";

import type { Tone } from "./labels";

type TierMeta = { name: string; tone: Tone; icon: LucideIcon; summary: string };

export const TIER_META: Record<string, TierMeta> = {
  T0: {
    name: "Abstain",
    tone: "neutral",
    icon: CircleSlashIcon,
    summary: "Tidak ada intervensi karena bukti belum memadai.",
  },
  T1: {
    name: "Inform",
    tone: "info",
    icon: InfoIcon,
    summary: "Informasi ketidaksesuaian ringan, tidak menahan klaim.",
  },
  T2: {
    name: "Recommend Review",
    tone: "warning",
    icon: EyeIcon,
    summary: "Direkomendasikan peninjauan oleh verifikator.",
  },
  T3: {
    name: "Flag for Human Verdict",
    tone: "danger",
    icon: FlagIcon,
    summary: "Disajikan untuk keputusan manusia.",
  },
};

type TierBadgeProps = {
  tier: string | null | undefined;
  compact?: boolean;
  className?: string;
};

export function TierBadge({ tier, compact = false, className }: TierBadgeProps) {
  if (!tier) return null;
  const meta = TIER_META[tier];
  if (!meta) return <Badge variant="neutral">{tier}</Badge>;
  const Icon = meta.icon;
  return (
    <Badge variant={meta.tone} className={className}>
      <Icon aria-hidden="true" />
      {compact ? tier : `${tier} ${meta.name}`}
    </Badge>
  );
}

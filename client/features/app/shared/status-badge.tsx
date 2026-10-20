import { Badge } from "@/components/ui/badge";

import { STATUS_TABLES, type StatusKind } from "./labels";

type StatusBadgeProps = {
  kind: StatusKind;
  value: string | null | undefined;
  className?: string;
};

export function StatusBadge({ kind, value, className }: StatusBadgeProps) {
  if (!value) return null;
  const entry = STATUS_TABLES[kind][value] ?? { label: value, tone: "neutral" as const };
  return (
    <Badge variant={entry.tone} className={className}>
      {entry.label}
    </Badge>
  );
}

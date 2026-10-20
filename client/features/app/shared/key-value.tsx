import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type KeyValueItem = { label: string; value: ReactNode };

type KeyValueListProps = {
  items: KeyValueItem[];
  columns?: 2 | 3;
  className?: string;
};

export function KeyValueList({ items, columns = 2, className }: KeyValueListProps) {
  return (
    <dl
      className={cn(
        "grid gap-x-6 gap-y-3 text-sm",
        columns === 3 ? "sm:grid-cols-2 lg:grid-cols-3" : "sm:grid-cols-2",
        className,
      )}
    >
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs font-medium text-muted-foreground">{item.label}</dt>
          <dd className="mt-0.5 break-words text-ink">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

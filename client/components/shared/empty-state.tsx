import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-3xl border border-dashed border-line bg-white px-6 py-12 text-center">
      <span className="grid size-11 place-items-center rounded-full bg-lavender text-brand">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <p className="text-base font-semibold text-ink">{title}</p>
      {description ? (
        <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

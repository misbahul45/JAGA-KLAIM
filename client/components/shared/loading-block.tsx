import { Skeleton } from "@/components/ui/skeleton";

type LoadingBlockProps = {
  rows?: number;
  label?: string;
};

export function LoadingBlock({ rows = 3, label = "Memuat data" }: LoadingBlockProps) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-10 w-full rounded-xl" />
      ))}
    </div>
  );
}

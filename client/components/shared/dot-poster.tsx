import { cn } from "@/lib/utils";

type DotPosterProps = {
  tone?: "light" | "dark";
  className?: string;
};

export function DotPoster({ tone = "light", className }: DotPosterProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "size-full",
        tone === "dark" ? "bg-dots-light" : "bg-dots opacity-80",
        className,
      )}
    />
  );
}

import { cn } from "@/lib/utils";

type LogoProps = {
  className?: string;
  tone?: "dark" | "light";
};

const DOTS = [
  { x: 5, y: 5, c: "var(--brand)" },
  { x: 12, y: 5, c: "var(--brand)" },
  { x: 19, y: 5, c: "var(--magenta)" },
  { x: 5, y: 12, c: "var(--brand)" },
  { x: 12, y: 12, c: "var(--mint)" },
  { x: 19, y: 12, c: "var(--brand)" },
  { x: 5, y: 19, c: "var(--brand)" },
  { x: 12, y: 19, c: "var(--brand)" },
  { x: 19, y: 19, c: "var(--orange)" },
];

export function Logo({ className, tone = "dark" }: LogoProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2.5 text-[1.05rem] font-semibold tracking-[-0.03em]",
        tone === "dark" ? "text-ink" : "text-white",
        className,
      )}
    >
      <svg viewBox="0 0 24 24" className="size-6" aria-hidden="true">
        {DOTS.map((dot) => (
          <circle key={`${dot.x}-${dot.y}`} cx={dot.x} cy={dot.y} r="2.4" fill={dot.c} />
        ))}
      </svg>
      <span>JAGA-KLAIM</span>
    </span>
  );
}

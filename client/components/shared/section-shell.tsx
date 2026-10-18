import type { ReactNode, Ref } from "react";

import { cn } from "@/lib/utils";

type SectionShellProps = {
  id: string;
  tone?: "light" | "tint" | "dark";
  className?: string;
  innerClassName?: string;
  ref?: Ref<HTMLElement>;
  children: ReactNode;
};

const TONES = {
  light: "bg-background text-foreground",
  tint: "bg-surface-2 text-foreground",
  dark: "bg-night text-white",
} as const;

export function SectionShell({
  id,
  tone = "light",
  className,
  innerClassName,
  ref,
  children,
}: SectionShellProps) {
  return (
    <section
      ref={ref}
      id={id}
      aria-labelledby={`${id}-title`}
      className={cn(
        "relative isolate overflow-hidden py-24 sm:py-32",
        TONES[tone],
        className,
      )}
    >
      <div
        className={cn(
          "mx-auto w-full max-w-6xl px-5 sm:px-8",
          innerClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
}

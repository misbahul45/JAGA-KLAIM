import { cn } from "@/lib/utils";

type SectionHeadingProps = {
  id: string;
  title: string;
  lead?: string;
  tone?: "light" | "dark";
  align?: "left" | "center";
  className?: string;
};

export function SectionHeading({
  id,
  title,
  lead,
  tone = "light",
  align = "left",
  className,
}: SectionHeadingProps) {
  return (
    <div
      data-reveal
      className={cn(
        "flex max-w-3xl flex-col gap-5",
        align === "center" && "mx-auto items-center text-center",
        className,
      )}
    >
      <h2
        id={`${id}-title`}
        className="text-4xl leading-[1.06] font-semibold tracking-[-0.04em] text-balance sm:text-5xl"
      >
        {title}
      </h2>
      {lead ? (
        <p
          className={cn(
            "text-base leading-relaxed text-pretty sm:text-lg",
            tone === "dark" ? "text-white/70" : "text-muted-foreground",
          )}
        >
          {lead}
        </p>
      ) : null}
    </div>
  );
}

import type { VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ButtonLinkProps = ComponentProps<"a"> & VariantProps<typeof buttonVariants>;

export function ButtonLink({
  className,
  variant,
  size,
  ...props
}: ButtonLinkProps) {
  return (
    <a className={cn(buttonVariants({ variant, size }), className)} {...props} />
  );
}

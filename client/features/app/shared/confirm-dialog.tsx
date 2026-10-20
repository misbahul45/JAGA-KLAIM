"use client";

import type { ReactNode } from "react";

import { ErrorNotice } from "@/components/shared/error-notice";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel: string;
  pendingLabel?: string;
  pending: boolean;
  error?: unknown;
  disabled?: boolean;
  tone?: "brand" | "destructive";
  wide?: boolean;
  onConfirm: () => void;
  children?: ReactNode;
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  pendingLabel = "Memproses...",
  pending,
  error,
  disabled = false,
  tone = "brand",
  wide = false,
  onConfirm,
  children,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => (pending ? undefined : onOpenChange(next))}>
      <DialogContent className={cn(wide && "sm:max-w-xl")}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        {children}
        <ErrorNotice error={error} />
        <DialogFooter>
          <Button variant="outline" disabled={pending} onClick={() => onOpenChange(false)}>
            Batal
          </Button>
          <Button
            variant={tone === "destructive" ? "destructive" : "brand"}
            disabled={pending || disabled}
            onClick={onConfirm}
          >
            {pending ? pendingLabel : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import type { VariantProps } from "class-variance-authority";
import { useState } from "react";

import { Field } from "@/components/shared/field";
import { Button, type buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAction } from "@/hooks/use-action";
import { apiFetch } from "@/lib/api";

import { ConfirmDialog } from "../shared/confirm-dialog";

type ActionButtonProps = {
  label: string;
  title: string;
  description: string;
  path: string;
  variant?: VariantProps<typeof buttonVariants>["variant"];
  tone?: "brand" | "destructive";
  withReason?: boolean;
  disabled?: boolean;
  onDone: () => void;
};

export function ActionButton({
  label,
  title,
  description,
  path,
  variant = "outline",
  tone = "brand",
  withReason = false,
  disabled = false,
  onDone,
}: ActionButtonProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const action = useAction(() =>
    apiFetch<unknown>(path, { method: "POST", json: withReason ? { reason: reason.trim() } : undefined }),
  );

  return (
    <>
      <Button
        variant={variant}
        size="sm"
        disabled={disabled}
        onClick={() => {
          action.reset();
          setOpen(true);
        }}
      >
        {label}
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={title}
        description={description}
        confirmLabel={label}
        tone={tone}
        pending={action.pending}
        error={action.error}
        disabled={withReason && reason.trim().length < 5}
        onConfirm={async () => {
          const result = await action.run();
          if (result !== undefined) {
            setOpen(false);
            setReason("");
            onDone();
          }
        }}
      >
        {withReason ? (
          <Field id={`reason-${path}`} label="Alasan" hint="Minimal 5 karakter; dicatat pada audit trail.">
            <Textarea
              id={`reason-${path}`}
              rows={3}
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </Field>
        ) : null}
      </ConfirmDialog>
    </>
  );
}

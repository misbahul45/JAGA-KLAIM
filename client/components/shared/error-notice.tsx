import { AlertCircleIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiRequestError, describeError } from "@/lib/api";

type ErrorNoticeProps = {
  error: unknown;
  title?: string;
  onRetry?: () => void;
};

export function ErrorNotice({ error, title, onRetry }: ErrorNoticeProps) {
  if (!error) return null;
  const forbidden = error instanceof ApiRequestError && error.status === 403;
  const heading =
    title ?? (forbidden ? "Akses ditolak" : "Permintaan tidak dapat diselesaikan");
  return (
    <Alert variant="destructive">
      <AlertCircleIcon aria-hidden="true" />
      <AlertTitle>{heading}</AlertTitle>
      <AlertDescription>
        <p>{describeError(error)}</p>
        {onRetry ? (
          <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
            Coba lagi
          </Button>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}

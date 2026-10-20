import type { ReactNode } from "react";

import { ErrorNotice } from "@/components/shared/error-notice";
import { LoadingBlock } from "@/components/shared/loading-block";
import type { ApiState } from "@/hooks/use-api";

type QueryBoundaryProps<T> = {
  state: ApiState<T>;
  rows?: number;
  children: (data: T) => ReactNode;
};

export function QueryBoundary<T>({ state, rows = 4, children }: QueryBoundaryProps<T>) {
  if (state.data === null) {
    if (state.error) return <ErrorNotice error={state.error} onRetry={state.reload} />;
    return <LoadingBlock rows={rows} />;
  }
  return (
    <>
      {state.error ? <ErrorNotice error={state.error} onRetry={state.reload} /> : null}
      {children(state.data)}
    </>
  );
}

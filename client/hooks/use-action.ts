"use client";

import { useCallback, useState } from "react";

export type ActionState<A extends unknown[], R> = {
  run: (...args: A) => Promise<R | undefined>;
  pending: boolean;
  error: unknown;
  reset: () => void;
};

export function useAction<A extends unknown[], R>(
  action: (...args: A) => Promise<R>,
): ActionState<A, R> {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const run = useCallback(
    async (...args: A): Promise<R | undefined> => {
      setPending(true);
      setError(null);
      try {
        return await action(...args);
      } catch (cause) {
        setError(cause);
        return undefined;
      } finally {
        setPending(false);
      }
    },
    [action],
  );

  const reset = useCallback(() => setError(null), []);

  return { run, pending, error, reset };
}

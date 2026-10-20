"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type Settled<T> = { key: string; data: T | null; error: unknown };

export type ApiState<T> = {
  data: T | null;
  error: unknown;
  loading: boolean;
  refreshing: boolean;
  reload: () => void;
};

export function useApi<T>(path: string | null): ApiState<T> {
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const [nonce, setNonce] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (path === null) return;
    const controller = new AbortController();

    apiFetch<T>(path, { signal: controller.signal })
      .then((data) => {
        setSettled({ key: path, data, error: null });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSettled((previous) => ({
          key: path,
          data: previous && previous.key === path ? previous.data : null,
          error,
        }));
      })
      .finally(() => {
        if (!controller.signal.aborted) setRefreshing(false);
      });

    return () => controller.abort();
  }, [path, nonce]);

  const reload = useCallback(() => {
    setRefreshing(true);
    setNonce((value) => value + 1);
  }, []);

  const current = settled && settled.key === path ? settled : null;

  return {
    data: current ? current.data : null,
    error: current ? current.error : null,
    loading: path !== null && current === null,
    refreshing,
    reload,
  };
}

"use client";

import { useEffect } from "react";

export function usePolling(active: boolean, reload: () => void, intervalMs = 3000): void {
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(reload, intervalMs);
    return () => window.clearInterval(timer);
  }, [active, reload, intervalMs]);
}

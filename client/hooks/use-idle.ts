import { useEffect, useState } from "react";

export function useIdle(timeout = 1200) {
  const [idle, setIdle] = useState(false);

  useEffect(() => {
    if (typeof window.requestIdleCallback === "function") {
      const handle = window.requestIdleCallback(() => setIdle(true), {
        timeout,
      });
      return () => window.cancelIdleCallback(handle);
    }
    const handle = window.setTimeout(() => setIdle(true), 200);
    return () => window.clearTimeout(handle);
  }, [timeout]);

  return idle;
}

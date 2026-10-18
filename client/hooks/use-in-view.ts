import { useEffect, useRef, useState } from "react";

type Options = {
  rootMargin?: string;
  once?: boolean;
};

export function useInView<T extends Element>({
  rootMargin = "0px",
  once = false,
}: Options = {}) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        setInView(entry.isIntersecting);
        if (entry.isIntersecting && once) observer.disconnect();
      },
      { rootMargin },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [rootMargin, once]);

  return [ref, inView] as const;
}

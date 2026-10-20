"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};
const clientYear = () => new Date().getFullYear();
const serverYear = () => null;

export function CopyrightYear() {
  const year = useSyncExternalStore(subscribe, clientYear, serverYear);
  return <>{year}</>;
}

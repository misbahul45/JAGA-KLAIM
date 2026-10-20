"use client";

import { createContext, useContext } from "react";

import type { Principal } from "@/lib/api-types";

export type AuthValue = {
  principal: Principal;
  can: (permission: string) => boolean;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthValue | null>(null);

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (value === null) throw new Error("useAuth harus dipakai di dalam AuthGate");
  return value;
}

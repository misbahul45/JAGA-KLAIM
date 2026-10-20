import type { Metadata } from "next";

import { PolicyView } from "@/features/app/governance/policy-view";

export const metadata: Metadata = { title: "Kebijakan tier" };

export default function PolicyPage() {
  return <PolicyView />;
}

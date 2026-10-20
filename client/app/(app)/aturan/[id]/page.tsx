import type { Metadata } from "next";

import { RuleVersionView } from "@/features/app/governance/rule-version-view";

export const metadata: Metadata = { title: "Versi aturan" };

export default function RuleVersionPage() {
  return <RuleVersionView />;
}

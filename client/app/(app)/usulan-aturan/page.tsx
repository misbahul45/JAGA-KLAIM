import type { Metadata } from "next";

import { RuleUpdatesView } from "@/features/app/governance/rule-updates-view";

export const metadata: Metadata = { title: "Usulan pembaruan aturan" };

export default function RuleUpdatesPage() {
  return <RuleUpdatesView />;
}

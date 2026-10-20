import type { Metadata } from "next";

import { RuleSetsView } from "@/features/app/governance/rule-sets-view";

export const metadata: Metadata = { title: "Aturan bukti" };

export default function RulesPage() {
  return <RuleSetsView />;
}

import type { Metadata } from "next";

import { ClaimListView } from "@/features/app/claims/claim-list-view";

export const metadata: Metadata = { title: "Klaim" };

export default function ClaimsPage() {
  return <ClaimListView />;
}

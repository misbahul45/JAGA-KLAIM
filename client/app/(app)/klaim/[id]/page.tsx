import type { Metadata } from "next";

import { ClaimDetailView } from "@/features/app/claims/claim-detail-view";

export const metadata: Metadata = { title: "Detail klaim" };

export default function ClaimDetailPage() {
  return <ClaimDetailView />;
}

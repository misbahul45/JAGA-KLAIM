import type { Metadata } from "next";

import { NewClaimView } from "@/features/app/claims/new-claim-view";

export const metadata: Metadata = { title: "Klaim baru" };

export default function NewClaimPage() {
  return <NewClaimView />;
}

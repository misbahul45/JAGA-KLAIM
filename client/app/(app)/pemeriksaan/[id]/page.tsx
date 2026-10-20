import type { Metadata } from "next";

import { RunDetailView } from "@/features/app/investigations/run-detail-view";

export const metadata: Metadata = { title: "Rincian pemeriksaan" };

export default function RunDetailPage() {
  return <RunDetailView />;
}

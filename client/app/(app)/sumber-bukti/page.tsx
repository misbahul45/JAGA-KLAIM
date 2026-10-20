import type { Metadata } from "next";

import { SourcesView } from "@/features/app/sources/sources-view";

export const metadata: Metadata = { title: "Sumber bukti" };

export default function SourcesPage() {
  return <SourcesView />;
}

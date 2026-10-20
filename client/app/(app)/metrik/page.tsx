import type { Metadata } from "next";

import { MetricsView } from "@/features/app/metrics/metrics-view";

export const metadata: Metadata = { title: "Metrik mutu" };

export default function MetricsPage() {
  return <MetricsView />;
}

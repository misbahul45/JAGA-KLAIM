import type { Metadata } from "next";

import { DashboardView } from "@/features/app/dashboard/dashboard-view";

export const metadata: Metadata = { title: "Dasbor" };

export default function DashboardPage() {
  return <DashboardView />;
}

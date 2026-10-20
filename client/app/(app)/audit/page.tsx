import type { Metadata } from "next";

import { AuditView } from "@/features/app/audit/audit-view";

export const metadata: Metadata = { title: "Log audit" };

export default function AuditPage() {
  return <AuditView />;
}

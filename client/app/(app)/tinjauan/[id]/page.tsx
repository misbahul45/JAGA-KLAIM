import type { Metadata } from "next";

import { WorkbenchView } from "@/features/app/review/workbench-view";

export const metadata: Metadata = { title: "Workbench verifikator" };

export default function WorkbenchPage() {
  return <WorkbenchView />;
}

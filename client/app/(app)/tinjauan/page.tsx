import type { Metadata } from "next";

import { ReviewQueueView } from "@/features/app/review/review-queue-view";

export const metadata: Metadata = { title: "Antrean tinjauan" };

export default function ReviewQueuePage() {
  return <ReviewQueueView />;
}

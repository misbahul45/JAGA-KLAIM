import type { Metadata } from "next";

import { UsersView } from "@/features/app/users/users-view";

export const metadata: Metadata = { title: "Pengguna" };

export default function UsersPage() {
  return <UsersView />;
}

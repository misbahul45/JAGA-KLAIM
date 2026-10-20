import type { Metadata } from "next";

import { AccountView } from "@/features/app/account/account-view";

export const metadata: Metadata = { title: "Akun" };

export default function AccountPage() {
  return <AccountView />;
}

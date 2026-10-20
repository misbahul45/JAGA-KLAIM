"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { buttonVariants } from "@/components/ui/button";

import { RequirePermission } from "../shared/require-permission";
import { SectionCard } from "../shared/section-card";
import { ClaimForm } from "./claim-form";

export function NewClaimView() {
  const router = useRouter();
  return (
    <RequirePermission permission="claim:write">
      <div className="space-y-6">
        <PageHeader
          title="Klaim baru"
          description="Masukkan hasil coding dan grouping. Klaim disimpan sebagai draf; pemeriksaan baru berjalan setelah Anda mengirim coding."
          actions={
            <Link href="/klaim" className={buttonVariants({ variant: "outline", size: "sm" })}>
              <ArrowLeftIcon aria-hidden="true" />
              Kembali
            </Link>
          }
        />
        <SectionCard title="Data klaim">
          <ClaimForm onDone={(claim) => router.replace(`/klaim/${claim.id}`)} />
        </SectionCard>
      </div>
    </RequirePermission>
  );
}

import { EvidenceAuthority } from "@/features/landing/evidence-authority/evidence-authority";
import { FaqCta } from "@/features/landing/faq-cta/faq-cta";
import { Governance } from "@/features/landing/governance/governance";
import { Hero } from "@/features/landing/hero/hero";
import { HowItWorks } from "@/features/landing/how-it-works/how-it-works";
import { ProblemSolution } from "@/features/landing/problem-solution/problem-solution";
import { RiskIntervention } from "@/features/landing/risk-intervention/risk-intervention";
import { SiteFooter } from "@/features/landing/site-footer/site-footer";
import { SiteHeader } from "@/features/landing/site-header/site-header";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main id="konten-utama" className="flex-1">
        <Hero />
        <ProblemSolution />
        <HowItWorks />
        <RiskIntervention />
        <EvidenceAuthority />
        <Governance />
        <FaqCta />
      </main>
      <SiteFooter />
    </>
  );
}

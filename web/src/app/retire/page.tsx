import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { RetireForm } from "@/components/retire-form";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = { title: "Retire credits" };

export default function RetirePage() {
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <PageHeader
        eyebrow="Registry operator"
        title="Retire credits for a buyer"
        description="Record whole lots of serials as retired on Sepolia. The buyer’s identity is encrypted for the auditor; only a commitment hash goes on-chain. This screen calls the local OnceSealed API, which holds the demo operator key."
        aside={<Badge tone="seal">Acting as: Registry operator (demo account)</Badge>}
      />
      <RetireForm />
    </main>
  );
}

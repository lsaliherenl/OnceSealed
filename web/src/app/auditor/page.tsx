import type { Metadata } from "next";
import { AuditQueue } from "@/components/audit-queue";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = { title: "Audit queue" };

export default function AuditorPage() {
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <PageHeader
        eyebrow="Accredited auditor"
        title="Audit queue"
        description="Open each sealed retirement, review the checks and attest once. Your decision is written on-chain and can’t be changed afterwards. This screen calls the local OnceSealed API, which holds the demo auditor key."
        aside={<Badge tone="seal">Acting as: Auditor (demo key)</Badge>}
      />
      <AuditQueue />
    </main>
  );
}

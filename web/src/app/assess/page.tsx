import type { Metadata } from "next";
import { AssessPanel } from "@/components/assess-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = { title: "Assess a project" };

export default function AssessPage() {
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <PageHeader
        eyebrow="Assessor"
        title="Assess a project"
        description="Add a registry document, run the AI-assisted checks and compare the draft with the published report before replacing it. Publishing anchors the new version on-chain; earlier versions stay readable. This screen calls the local OnceSealed API, which holds the demo assessor key and the model API key."
        aside={<Badge tone="seal">Acting as: Assessor (demo key)</Badge>}
      />
      <AssessPanel />
    </main>
  );
}

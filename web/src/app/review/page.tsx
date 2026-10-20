import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { ReviewQueue } from "@/components/review-queue";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = { title: "Review flagged checks" };

export default function ReviewPage() {
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <PageHeader
        eyebrow="Assessor"
        title="Review flagged checks"
        description="Where the checklist model and the second model disagree, a person reads the excerpt the models read and decides. The decision replaces the models’ answer in the score; both answers stay visible in the report. This screen calls the local OnceSealed API."
        aside={<Badge tone="seal">Acting as: Assessor (demo key)</Badge>}
      />
      <ReviewQueue />
    </main>
  );
}

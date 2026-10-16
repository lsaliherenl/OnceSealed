import { Link2 } from "lucide-react";
import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/page-header";
import { Callout } from "@/components/ui/card";
import { VerifyPanel } from "@/components/verify-panel";

export const metadata: Metadata = { title: "Verify a retirement" };

type SearchParams = Promise<{ q?: string | string[] }>;

export default function VerifyPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <PageHeader
        eyebrow="Public verification · no account needed"
        title="Verify a retirement"
        description="Look up the public record, then check a receipt against it. Anyone can do this; only the receipt holder can prove the claim."
        aside={
          <Callout tone="ok" icon={<Link2 aria-hidden />} className="flex-[0_1_420px]">
            <strong>Verified directly against the blockchain from your browser.</strong> This page reads the Sepolia
            contract through a public RPC. No OnceSealed server sits in between.
          </Callout>
        }
      />
      <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
        <VerifyPanelFromQuery searchParams={searchParams} />
      </Suspense>
    </main>
  );
}

/** The lookup box in the top bar sends ?q=1 or ?q=SIM-…; a new query remounts the panel. */
async function VerifyPanelFromQuery({ searchParams }: { searchParams: SearchParams }) {
  const raw = (await searchParams).q;
  const q = (Array.isArray(raw) ? raw[0] : raw) ?? "";
  return <VerifyPanel key={q} q={q} />;
}

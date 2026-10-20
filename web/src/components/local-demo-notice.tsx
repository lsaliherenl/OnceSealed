import { Terminal } from "lucide-react";
import { TransitionLink } from "@/components/transition-link";
import { Callout } from "@/components/ui/card";
import { REPO_URL } from "@/lib/data";

/** The technical error helps on a local demo; on the hosted site the API is absent by design. */
const isLocal = () => typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

/**
 * Shown by the operator, auditor and assessor screens when the local API does not answer. These screens hold
 * test-network keys, so they only run on a local demo; the hosted site keeps the public pages.
 */
export function LocalDemoNotice({ role, detail }: { role: string; detail?: string | null }) {
  return (
    <Callout tone="seal" icon={<Terminal aria-hidden />}>
      <span className="flex flex-col gap-2">
        <span>
          <strong>The {role} screen runs on the local demo.</strong> It signs Sepolia transactions with the demo{" "}
          {role} key, so it is not served from the public site. To try it, clone the repository and run{" "}
          <code className="font-mono text-[13px]">python scripts/demo_up.py</code> (or{" "}
          <code className="font-mono text-[13px]">--local</code> for a throwaway chain without any keys); see the{" "}
          <a href={`${REPO_URL}#run-the-full-demo`} target="_blank" rel="noopener noreferrer">
            README
          </a>
          .
        </span>
        <span>
          What it produced is public: retirements{" "}
          {[1, 3, 4].map((n, i) => (
            <span key={n}>
              {i > 0 ? ", " : ""}
              <TransitionLink href={`/verify?q=${n}`}>#{n}</TransitionLink>
            </span>
          ))}{" "}
          and their audits on the verify page, and every anchored report version on the{" "}
          <TransitionLink href="/projects">project pages</TransitionLink>.
        </span>
        {detail && isLocal() && <span className="text-[12px] opacity-75">({detail})</span>}
      </span>
    </Callout>
  );
}

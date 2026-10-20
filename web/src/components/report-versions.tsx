"use client";

import { Check, LoaderCircle, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { EtherscanLink } from "@/components/hash";
import { Card } from "@/components/ui/card";
import { getReport, reportHash } from "@/lib/chain";
import type { Anchor } from "@/lib/data";

type CheckState = "checking" | "matches" | "differs" | "error";

/**
 * Every version of the project's report anchored on Sepolia. For each one the browser downloads the archived
 * file, hashes it and compares the hash with `getReport(project, version)` read from the contract, so a
 * retirement made under an older report can still be checked against the report it recorded.
 */
export function ReportVersions({ projectId, anchors }: { projectId: string; anchors: Anchor[] }) {
  const [checks, setChecks] = useState<Record<number, CheckState>>({});

  useEffect(() => {
    let live = true;
    for (const a of anchors) {
      Promise.all([fetch(a.file).then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status))))), getReport(projectId, a.version)])
        .then(([text, onChain]) => live && setChecks((c) => ({ ...c, [a.version]: reportHash(text) === onChain.reportHash.toLowerCase() ? "matches" : "differs" })))
        .catch(() => live && setChecks((c) => ({ ...c, [a.version]: "error" })));
    }
    return () => {
      live = false;
    };
  }, [projectId, anchors]);

  const latest = anchors.at(-1)?.version;
  return (
    <section aria-labelledby="versions-h" className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 id="versions-h" className="text-xl font-semibold">
          Report versions
        </h2>
        <p className="text-[13px] text-muted-foreground">
          Every version anchored on Sepolia stays readable: a retirement records the version current when it happened.
          Each file is hashed in your browser and compared with that version on the contract.
        </p>
      </div>
      <Card className="overflow-hidden">
        <ol reversed>
          {[...anchors].reverse().map((a) => {
            const state = checks[a.version] ?? "checking";
            return (
              <li
                key={a.version}
                id={`report-v${a.version}`}
                className="flex scroll-mt-24 flex-wrap items-center gap-x-6 gap-y-2 border-t border-border px-6 py-3.5 first:border-t-0 target:bg-primary-soft"
              >
                <span className="w-24 font-mono text-[13px] font-semibold">
                  v{a.version}
                  {a.version === latest ? <span className="font-sans font-normal text-muted-foreground"> · latest</span> : null}
                </span>
                <span className="w-28 text-[13px] text-muted-foreground tabular-nums">{a.generated_at.slice(0, 10)}</span>
                <span className="w-24 text-[13px] tabular-nums">overall {a.overall}/100</span>
                <span className="w-20 font-mono text-[12px] text-muted-foreground">{a.schema}</span>
                <span className="inline-flex min-w-48 flex-1 items-center gap-1.5 text-[13px]">
                  {state === "checking" && (
                    <>
                      <LoaderCircle aria-hidden className="size-3.5 animate-spin text-muted-foreground" /> checking…
                    </>
                  )}
                  {state === "matches" && (
                    <span className="inline-flex items-center gap-1.5 text-ok">
                      <Check aria-hidden className="size-3.5" /> file matches the chain
                    </span>
                  )}
                  {state === "differs" && (
                    <span className="inline-flex items-center gap-1.5 text-bad">
                      <TriangleAlert aria-hidden className="size-3.5" /> file differs from the chain
                    </span>
                  )}
                  {state === "error" && <span className="text-muted-foreground">could not check (network)</span>}
                </span>
                <a href={a.file} download={`${projectId}-v${a.version}.json`} className="text-[13px]">
                  Download
                </a>
                <EtherscanLink hash={a.tx} />
              </li>
            );
          })}
        </ol>
      </Card>
    </section>
  );
}

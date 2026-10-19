"use client";

import { Check, LoaderCircle, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { latestReport, reportHash } from "@/lib/chain";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; version: number; score: number; fileHash: string; onChain: string };

/**
 * Downloads the published report file, hashes it in the browser (keccak256 of canonical JSON, as the Python
 * code does) and compares the result with the latest report anchored on Sepolia, read live from the contract.
 * `pageHash` is the hash of the report this page was built from, so a stale page is caught too.
 */
export function AnchorCheck({ projectId, pageHash }: { projectId: string; pageHash: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let live = true;
    Promise.all([
      fetch(`/reports/${projectId}.json`).then((r) => {
        if (!r.ok) throw new Error(`Published report not found (${r.status})`);
        return r.text();
      }),
      latestReport(projectId),
    ])
      .then(([text, onChain]) => {
        if (!live) return;
        if (!onChain) setState({ kind: "error", message: "No report anchored on-chain for this project." });
        else setState({ kind: "done", version: onChain.version, score: onChain.score, fileHash: reportHash(text), onChain: onChain.reportHash.toLowerCase() });
      })
      .catch((e: unknown) => live && setState({ kind: "error", message: e instanceof Error ? e.message.split("\n")[0] : "RPC error" }));
    return () => {
      live = false;
    };
  }, [projectId]);

  if (state.kind === "loading") {
    return (
      <span className="inline-flex items-center gap-2 text-[13px] text-muted-foreground">
        <LoaderCircle aria-hidden className="size-4 animate-spin" />
        Hashing the published file and reading the contract on Sepolia…
      </span>
    );
  }
  if (state.kind === "error") {
    return (
      <span className="inline-flex items-center gap-2 text-[13px] text-bad">
        <TriangleAlert aria-hidden className="size-4" />
        {state.message}
      </span>
    );
  }
  if (state.fileHash !== state.onChain) {
    return (
      <span className="inline-flex items-center gap-2 text-[13px] font-semibold text-bad" aria-live="polite">
        <TriangleAlert aria-hidden className="size-4" />
        Does not match on-chain version {state.version}: the published file differs from what was anchored
      </span>
    );
  }
  return (
    <span className="inline-flex flex-col gap-0.5 text-[13px]" aria-live="polite">
      <span className="inline-flex items-center gap-2 font-semibold text-ok">
        <Check aria-hidden className="size-4" />
        Matches on-chain version {state.version} (score {state.score})
      </span>
      <span className="text-muted-foreground">
        Your browser hashed the published file itself and read the contract on Sepolia directly.
      </span>
      {state.fileHash !== pageHash.toLowerCase() && (
        <span className="font-semibold text-warn">This page was built from an older report file; reload for the current one.</span>
      )}
    </span>
  );
}

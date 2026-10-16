"use client";

import { Check, LoaderCircle, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { latestReport } from "@/lib/chain";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; version: number; matches: boolean; score: number };

/** Reads the latest anchored report from Sepolia in the browser and compares it with the published file. */
export function AnchorCheck({ projectId, reportHash }: { projectId: string; reportHash: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let live = true;
    latestReport(projectId)
      .then((r) => {
        if (!live) return;
        if (!r) setState({ kind: "error", message: "No report anchored on-chain for this project." });
        else setState({ kind: "done", version: r.version, score: r.score, matches: r.reportHash.toLowerCase() === reportHash.toLowerCase() });
      })
      .catch((e: unknown) => live && setState({ kind: "error", message: e instanceof Error ? e.message.split("\n")[0] : "RPC error" }));
    return () => {
      live = false;
    };
  }, [projectId, reportHash]);

  if (state.kind === "loading") {
    return (
      <span className="inline-flex items-center gap-2 text-[13px] text-muted-foreground">
        <LoaderCircle aria-hidden className="size-4 animate-spin" />
        Reading the contract on Sepolia…
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
  return state.matches ? (
    <span className="inline-flex items-center gap-2 text-[13px] font-semibold text-ok" aria-live="polite">
      <Check aria-hidden className="size-4" />
      Matches on-chain version {state.version} (score {state.score}), read live from Sepolia
    </span>
  ) : (
    <span className="inline-flex items-center gap-2 text-[13px] font-semibold text-bad" aria-live="polite">
      <TriangleAlert aria-hidden className="size-4" />
      Does not match on-chain version {state.version}: the published file differs from what was anchored
    </span>
  );
}

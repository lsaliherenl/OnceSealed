import { Info, Table2 } from "lucide-react";
import { Tag } from "@/components/ui/card";
import { ICVCM_LABEL, type IcvcmStatus, PRINCIPLE_TONE, type PrincipleStatus } from "@/lib/data";
import { cn, staggerStyle } from "@/lib/utils";

const stampTone: Record<IcvcmStatus, string> = {
  approved_with_conditions: "text-ok",
  not_approved: "text-bad",
  not_ccp_approved: "text-risk",
  under_assessment: "text-na border-dashed",
  unknown: "text-na border-dashed",
};

/**
 * ICVCM methodology status. Square corners and a solid border on purpose,
 * so it never reads like the rounded AI finding badges.
 */
export function IcvcmStamp({
  status,
  size = "sm",
  className,
}: {
  status: IcvcmStatus;
  size?: "sm" | "lg";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded border-[1.5px] border-current bg-card font-semibold whitespace-nowrap transition-colors duration-300",
        size === "lg" ? "min-h-10 px-3.5 py-1.5 text-base" : "min-h-[30px] px-2.5 py-1 text-[13px]",
        stampTone[status],
        className,
      )}
    >
      <span aria-hidden className="size-2 rounded-full bg-current" />
      {ICVCM_LABEL[status]}
    </span>
  );
}

export function DeterministicTag({ children = "Deterministic · not AI", className }: { children?: React.ReactNode; className?: string }) {
  return (
    <Tag className={className}>
      <Table2 aria-hidden />
      {children}
    </Tag>
  );
}

export function SignalBanner({ children }: { children: React.ReactNode }) {
  return (
    <div role="note" className="flex flex-wrap items-start gap-x-4 gap-y-3 rounded-xl bg-warn-soft px-5 py-4 transition-colors duration-300">
      <Info aria-hidden className="mt-0.5 size-5 shrink-0 text-warn" />
      <p className="flex-[1_1_400px]">
        <strong>Signal, not verdict.</strong> {children}
      </p>
    </div>
  );
}

const fill: Record<string, string> = { ok: "bg-ok", warn: "bg-warn", risk: "bg-risk", bad: "bg-bad", na: "bg-na" };

export function ScoreBar({ status, score, index = 0 }: { status: PrincipleStatus; score: number | null; index?: number }) {
  return (
    <div
      role="img"
      aria-label={score == null ? "Evidence score not applicable" : `Evidence score ${score} out of 100`}
      className="h-2 overflow-hidden rounded-full bg-secondary"
    >
      <div
        className={cn("animate-grow stagger-slow h-full origin-left rounded-full", fill[PRINCIPLE_TONE[status]])}
        style={{ ...staggerStyle(index), width: `${score ?? 0}%` }}
      />
    </div>
  );
}

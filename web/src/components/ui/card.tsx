import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border/80 bg-card/85 shadow-[0_10px_30px_-22px_rgba(10,30,22,0.45)] backdrop-blur-md transition-colors duration-300",
        className,
      )}
      {...props}
    />
  );
}

export function Eyebrow({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-xs leading-4 font-semibold tracking-[0.08em] text-muted-foreground uppercase", className)}
      {...props}
    />
  );
}

/** Small uppercase tag — used to mark the deterministic ICVCM lookup. */
export function Tag({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[11px] leading-[14px] font-semibold tracking-[0.06em] text-seal uppercase [&_svg]:size-3.5",
        className,
      )}
      {...props}
    />
  );
}

type CalloutTone = "seal" | "warn" | "ok" | "bad" | "neutral";

const calloutTone: Record<CalloutTone, string> = {
  seal: "bg-seal-soft [&>svg]:text-seal",
  warn: "bg-warn-soft [&>svg]:text-warn",
  ok: "bg-ok-soft [&>svg]:text-ok",
  bad: "bg-bad-soft [&>svg]:text-bad",
  neutral: "bg-secondary [&>svg]:text-muted-foreground",
};

export function Callout({
  tone = "neutral",
  icon,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { tone?: CalloutTone; icon?: React.ReactNode }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-[10px] px-4 py-3.5 text-sm leading-normal transition-colors duration-300 [&>svg]:mt-0.5 [&>svg]:size-[18px] [&>svg]:shrink-0",
        calloutTone[tone],
        className,
      )}
      {...props}
    >
      {icon}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Two-column key/value list. */
export function KeyValue({ className, ...props }: React.HTMLAttributes<HTMLDListElement>) {
  return (
    <dl
      className={cn(
        "grid grid-cols-[minmax(0,150px)_minmax(0,1fr)] items-center gap-x-5 gap-y-3 [&_dd]:min-w-0 [&_dt]:text-[13px] [&_dt]:text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

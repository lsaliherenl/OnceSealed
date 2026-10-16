import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex min-h-6 items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-4 transition-colors duration-300",
  {
    variants: {
      tone: {
        neutral: "border-border bg-card text-muted-foreground",
        ok: "border-transparent bg-ok-soft text-ok",
        warn: "border-transparent bg-warn-soft text-warn",
        risk: "border-transparent bg-risk-soft text-risk",
        bad: "border-transparent bg-bad-soft text-bad",
        na: "border-transparent bg-na-soft text-na",
        seal: "border-transparent bg-seal-soft text-seal",
        ghost: "border-border bg-transparent text-muted-foreground opacity-60",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export type Tone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;

type BadgeProps = React.HTMLAttributes<HTMLElement> &
  VariantProps<typeof badgeVariants> & {
    /** Show a leading status dot. */
    dot?: boolean;
    as?: "span" | "li";
  };

export function Badge({ className, tone, dot, as: Tag = "span", children, ...props }: BadgeProps) {
  return (
    <Tag className={cn(badgeVariants({ tone }), className)} {...props}>
      {dot && <span aria-hidden className="size-2 shrink-0 rounded-full bg-current" />}
      {children}
    </Tag>
  );
}

import * as React from "react";
import { cn } from "@/lib/utils";

const field =
  "w-full min-h-11 rounded-lg border border-input bg-card px-3 text-[15px] text-foreground transition-[border-color,box-shadow,background-color] duration-300 aria-invalid:border-bad aria-invalid:shadow-[0_0_0_3px_var(--bad-soft)]";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(field, className)} {...props} />;
}

/** Native <select> styled like the inputs (keeps the prototype dependency-free). */
export function NativeSelect({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(field, "cursor-pointer", className)} {...props} />;
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-[13px] text-muted-foreground", className)} {...props} />;
}

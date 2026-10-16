import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-lg border px-[18px] text-sm font-semibold no-underline transition-[background-color,border-color,color,transform,box-shadow] duration-300 ease-out active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        outline: "border-input bg-card text-foreground hover:bg-secondary hover:text-foreground",
        primary:
          "border-primary bg-primary text-primary-foreground hover:border-primary-hover hover:bg-primary-hover hover:text-primary-foreground",
        seal: "border-seal bg-seal text-card hover:opacity-90 hover:text-card",
        danger: "border-bad bg-card text-bad hover:bg-bad-soft hover:text-bad",
      },
      size: {
        default: "",
        sm: "min-h-9 px-3",
      },
    },
    defaultVariants: { variant: "outline", size: "default" },
  },
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, type = "button", ...props }: ButtonProps) {
  return <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export function IconButton({ className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "inline-grid size-11 cursor-pointer place-items-center rounded-lg border border-border bg-card text-foreground transition-[background-color,border-color,transform] duration-300 hover:bg-secondary active:scale-[0.97] [&_svg]:size-[18px]",
        className,
      )}
      {...props}
    />
  );
}

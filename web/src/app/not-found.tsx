import { TransitionLink } from "@/components/transition-link";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col items-start gap-4 px-6 md:px-8 pt-10 pb-[72px]">
      <h1 className="text-[34px] leading-tight font-semibold tracking-[-0.02em]">Page not found</h1>
      <p className="text-muted-foreground">This page isn’t part of the prototype.</p>
      <TransitionLink href="/" className={buttonVariants({ variant: "primary" })}>
        Back to overview
      </TransitionLink>
    </main>
  );
}

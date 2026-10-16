"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type * as React from "react";

type Props = Omit<React.ComponentProps<typeof Link>, "href"> & { href: string };

/**
 * A next/link that fades the current page out (html[data-leaving], see
 * globals.css) before navigating. The new page's template clears the flag
 * and plays its entrance animation. Modified clicks and reduced motion skip
 * the delay.
 */
export function TransitionLink({ href, onClick, target, ...props }: Props) {
  const router = useRouter();

  return (
    <Link
      href={href}
      target={target}
      onClick={(e) => {
        onClick?.(e);
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (target && target !== "_self") return;
        if (href === window.location.pathname) return;
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        e.preventDefault();
        const root = document.documentElement;
        root.dataset.leaving = "";
        window.setTimeout(() => router.push(href), 200);
        // Safety net in case navigation is cancelled.
        window.setTimeout(() => delete root.dataset.leaving, 1500);
      }}
      {...props}
    />
  );
}

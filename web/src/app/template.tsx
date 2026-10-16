"use client";

import { useEffect } from "react";

/**
 * Templates remount on every navigation, so this is where the incoming page
 * clears the "leaving" flag set by TransitionLink and fades back in.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    delete document.documentElement.dataset.leaving;
  }, []);

  return <div className="page-stage">{children}</div>;
}

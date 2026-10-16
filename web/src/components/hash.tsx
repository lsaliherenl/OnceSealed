"use client";

import { Copy, ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { SEPOLIA_ETHERSCAN, cn, truncateHash } from "@/lib/utils";

/** Truncated monospace hash with a copy button. */
export function HashChip({ value, label, className }: { value: string; label: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const t = window.setTimeout(() => setCopied(false), 1500);
    return () => window.clearTimeout(t);
  }, [copied]);

  return (
    <button
      type="button"
      title={value}
      aria-label={`Copy ${label}`}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
        } catch {
          /* clipboard can be blocked; still show feedback */
        }
        setCopied(true);
      }}
      className={cn(
        // ::after extends the hit area to 44px tall without changing the chip size
        "relative inline-flex min-h-[34px] cursor-pointer items-center gap-1.5 rounded-md border border-border bg-secondary pr-1.5 pl-2.5 whitespace-nowrap text-foreground transition-colors duration-300 after:absolute after:inset-x-0 after:-inset-y-[5px] after:content-[''] hover:border-input",
        className,
      )}
    >
      <code className="font-mono text-[13px]">{truncateHash(value)}</code>
      {copied ? (
        <span className="pr-1 text-xs font-semibold text-ok" aria-live="polite">
          Copied
        </span>
      ) : (
        <Copy aria-hidden className="size-[15px] text-muted-foreground" />
      )}
    </button>
  );
}

/** Link to Sepolia Etherscan for a tx or address. */
export function EtherscanLink({
  hash,
  kind = "tx",
  children,
  className,
}: {
  hash: string;
  kind?: "tx" | "address";
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <a
      href={`${SEPOLIA_ETHERSCAN}/${kind}/${hash}`}
      target="_blank"
      rel="noopener noreferrer"
      className={cn("inline-flex min-h-11 items-center gap-1.5 font-medium", className)}
    >
      {children ?? <code className="font-mono text-[13px]">{truncateHash(hash)}</code>}
      <ExternalLink aria-hidden className="size-3.5" />
      <span className="sr-only">(opens Sepolia Etherscan in a new tab)</span>
    </a>
  );
}

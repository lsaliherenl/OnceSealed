import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** "0x7f3a…c91e" — first 6 and last 4 characters. */
export function truncateHash(full: string) {
  return `${full.slice(0, 6)}…${full.slice(-4)}`;
}

/** Zero-pads a simulated serial number to 6 digits. */
export function pad6(n: number) {
  return String(n).padStart(6, "0");
}

export function formatInt(n: number) {
  return n.toLocaleString("en-US");
}

/** Index for staggered entrance animations (read by the `stagger` utility). */
export function staggerStyle(i: number) {
  return { "--i": i } as React.CSSProperties;
}

export const SEPOLIA_ETHERSCAN = "https://sepolia.etherscan.io";

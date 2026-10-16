"use client";

import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { SCENE_PATHS } from "./scene-paths";

const BIRDS = [
  [968, 118, 1],
  [1000, 100, 0.8],
  [1032, 126, 0.9],
  [944, 140, 0.7],
] as const;

/**
 * Misty forest, river and low sun drawn behind the whole app (sidebar
 * included). Colors come from the theme tokens (--sky-*, --sun, --m1…--m4,
 * --river, --mist, --bird) so it follows light/dark mode. Page headings sit
 * in the sky; content cards sit over the treeline. Taller on the overview.
 */
export function Scene() {
  const pathname = usePathname();
  const tall = pathname === "/";

  return (
    <div
      aria-hidden
      className={cn(
        "scene pointer-events-none absolute inset-x-0 top-0 -z-10 overflow-hidden transition-[height] duration-700 ease-out",
        tall ? "h-[720px]" : "h-[500px]",
      )}
    >
      <svg className="block size-full" viewBox="0 0 1440 560" preserveAspectRatio="xMidYMax slice" focusable="false">
        <defs>
          <linearGradient id="os-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" style={{ stopColor: "var(--sky-top)" }} />
            <stop offset="0.62" style={{ stopColor: "var(--sky-bot)" }} />
          </linearGradient>
          <radialGradient id="os-sun">
            <stop offset="0" style={{ stopColor: "var(--sun)", stopOpacity: 1 }} />
            <stop offset="0.28" style={{ stopColor: "var(--sun)", stopOpacity: 0.55 }} />
            <stop offset="1" style={{ stopColor: "var(--sun)", stopOpacity: 0 }} />
          </radialGradient>
          <linearGradient id="os-fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0.68" style={{ stopColor: "var(--bg)", stopOpacity: 0 }} />
            <stop offset="1" style={{ stopColor: "var(--bg)", stopOpacity: 1 }} />
          </linearGradient>
          <filter id="os-blur" x="-30%" y="-200%" width="160%" height="500%">
            <feGaussianBlur stdDeviation="16" />
          </filter>
        </defs>

        <rect width="1440" height="560" style={{ fill: "url(#os-sky)" }} />
        <circle
          className="sun"
          cx="1060"
          cy="215"
          r="200"
          style={{ fill: "url(#os-sun)", transformBox: "fill-box", transformOrigin: "center" }}
        />
        <g className="birds" fill="none" strokeWidth="1.6" strokeLinecap="round" style={{ stroke: "var(--bird)" }}>
          {BIRDS.map(([x, y, s]) => (
            <path key={`${x}-${y}`} d={`M${x} ${y} q${5 * s} ${-4 * s} ${10 * s} 0 q${5 * s} ${-4 * s} ${10 * s} 0`} />
          ))}
        </g>

        <path className="l1" style={{ fill: "var(--m1)" }} d={SCENE_PATHS.far} />
        <g className="mist-a" filter="url(#os-blur)">
          <ellipse cx="360" cy="296" rx="380" ry="26" style={{ fill: "var(--mist)" }} />
          <ellipse cx="1080" cy="270" rx="340" ry="22" style={{ fill: "var(--mist)" }} />
        </g>
        <path className="l2" style={{ fill: "var(--m2)" }} d={SCENE_PATHS.mid} />
        <path className="l3" style={{ fill: "var(--m3)" }} d={SCENE_PATHS.treesBack} />
        <path className="l3" style={{ fill: "var(--river)" }} d={SCENE_PATHS.river} />
        <g className="mist-b" filter="url(#os-blur)">
          <ellipse cx="760" cy="392" rx="560" ry="22" style={{ fill: "var(--mist)" }} />
        </g>
        <path className="l4" style={{ fill: "var(--m4)" }} d={SCENE_PATHS.treesFrontLeft} />
        <path className="l4" style={{ fill: "var(--m4)" }} d={SCENE_PATHS.treesFrontRight} />
        <rect width="1440" height="560" style={{ fill: "url(#os-fade)" }} />
      </svg>
    </div>
  );
}

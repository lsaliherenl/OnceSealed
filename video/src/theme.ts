import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadSans } from "@remotion/google-fonts/IBMPlexSans";

// Same typefaces and light-theme tokens as the site (web/src/app/globals.css).
export const sans = loadSans("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin"] }).fontFamily;
export const mono = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;

export const C = {
  bg: "#f3f4ef",
  surface: "#ffffff",
  surface2: "#ecf0ea",
  text: "#13201b",
  muted: "#43504a",
  border: "#d8e0db",
  primary: "#1e5c47",
  primarySoft: "#e2eee8",
  seal: "#2f4c7a",
  sealSoft: "#e5ebf4",
  warn: "#835500",
  warnSoft: "#fbefd6",
  bad: "#a02b2b",
  badSoft: "#f8e0e0",
  strip: "#13201b",
  stripFg: "#dce6e1",
};

export type Tone = "primary" | "seal" | "warn" | "bad";
export const TONE: Record<Tone, [string, string]> = {
  primary: [C.primary, C.primarySoft],
  seal: [C.seal, C.sealSoft],
  warn: [C.warn, C.warnSoft],
  bad: [C.bad, C.badSoft],
};

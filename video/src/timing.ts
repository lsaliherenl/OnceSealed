import { useCurrentFrame } from "remotion";
import narration from "./narration.generated.json";

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
/** Seconds of picture before the voice starts, and after it ends. */
export const LEAD = 0.4;
export const TAIL = 0.5;
/** The closing scene holds the end card a little longer. */
const EXTRA: Record<string, number> = { closing: 3.5 };

export type Caption = { text: string; start: number; end: number };
export type Scene = { id: string; text: string; audio: string; duration: number; captions: Caption[]; frames: number };

export const SCENES: Scene[] = narration.scenes.map((s) => ({
  ...s,
  frames: Math.ceil((LEAD + s.duration + TAIL + (EXTRA[s.id] ?? 0)) * FPS),
}));
export const TOTAL_FRAMES = SCENES.reduce((sum, s) => sum + s.frames, 0);

/** Seconds since this scene's voice started (negative during the lead-in). */
export const useT = () => useCurrentFrame() / FPS - LEAD;

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

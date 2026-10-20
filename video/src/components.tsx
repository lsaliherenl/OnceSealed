import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile } from "remotion";
import { C, mono, sans, TONE, type Tone } from "./theme";
import { clamp01, type Caption, useT } from "./timing";

const ease = Easing.bezier(0.2, 0.7, 0.2, 1);
const move = Easing.inOut(Easing.cubic);

/** 0 → 1 over `dur` seconds from `at` (voice time). */
export const useIn = (at: number, dur = 0.5) => ease(clamp01((useT() - at) / dur));

// ---------------------------------------------------------------- layout

export const FRAME = { left: 160, top: 96, width: 1600, height: 820 };

export const Kicker: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const p = useIn(-0.3, 0.6);
  return (
    <div
      style={{
        position: "absolute",
        left: FRAME.left,
        top: 34,
        fontFamily: mono,
        fontSize: 22,
        letterSpacing: 3,
        color: C.primary,
        fontWeight: 500,
        opacity: p,
        transform: `translateY(${(1 - p) * 10}px)`,
        display: "flex",
        alignItems: "center",
        gap: 18,
      }}
    >
      {children}
      <span style={{ width: 80, height: 2, background: C.primary, opacity: 0.5 }} />
    </div>
  );
};

// ---------------------------------------------------------------- screenshot with a moving camera

/** Camera state: (cx, cy) is the image point (0-1) kept at the centre of the frame; z = 1 fits the width. */
export type Key = { at: number; cx: number; cy: number; z: number };
/** Highlight box in image coordinates (0-1), shown from `from` to `to` seconds. */
export type Box = { from: number; to?: number; x: number; y: number; w: number; h: number; tone?: Tone };

const MOVE = 1.2;

function camera(keys: Key[], t: number) {
  let s = keys[0];
  for (const k of keys.slice(1)) {
    const p = move(clamp01((t - k.at) / MOVE));
    if (p <= 0) break;
    s = { at: k.at, cx: s.cx + (k.cx - s.cx) * p, cy: s.cy + (k.cy - s.cy) * p, z: s.z + (k.z - s.z) * p };
  }
  return s;
}

export const Shot: React.FC<{
  src: string;
  keys: Key[];
  boxes?: Box[];
  /** width / height of the image */
  aspect?: number;
  /** voice time at which this shot's own clock starts */
  offset?: number;
  opacity?: number;
}> = ({ src, keys, boxes = [], aspect = 1.5, offset = 0, opacity = 1 }) => {
  const t = useT() - offset;
  const { width: W, height: H } = FRAME;
  const cam = camera(keys, t);
  const iw = W * cam.z;
  const ih = iw / aspect;
  const left = iw <= W ? (W - iw) / 2 : Math.min(0, Math.max(W - iw, W / 2 - cam.cx * iw));
  const top = ih <= H ? (H - ih) / 2 : Math.min(0, Math.max(H - ih, H / 2 - cam.cy * ih));
  return (
    <div
      style={{
        position: "absolute",
        ...FRAME,
        borderRadius: 24,
        overflow: "hidden",
        background: C.surface,
        border: `1px solid ${C.border}`,
        boxShadow: "0 30px 80px rgba(19,32,27,0.18), 0 6px 18px rgba(19,32,27,0.08)",
        opacity,
      }}
    >
      <div style={{ position: "absolute", left, top, width: iw, height: ih }}>
        <Img src={staticFile(`shots/${src}`)} style={{ width: "100%", height: "100%" }} />
        {boxes.map((b, i) => (
          <Highlight key={i} box={b} t={t} iw={iw} ih={ih} />
        ))}
      </div>
    </div>
  );
};

const Highlight: React.FC<{ box: Box; t: number; iw: number; ih: number }> = ({ box, t, iw, ih }) => {
  const [line, soft] = TONE[box.tone ?? "primary"];
  const inP = ease(clamp01((t - box.from) / 0.45));
  const outP = box.to === undefined ? 1 : 1 - clamp01((t - box.to) / 0.35);
  const o = Math.min(inP, outP);
  if (o <= 0) return null;
  const pad = 10;
  const pulse = 1 + 0.25 * Math.max(0, Math.sin(clamp01((t - box.from) / 1.2) * Math.PI));
  return (
    <div
      style={{
        position: "absolute",
        left: box.x * iw - pad,
        top: box.y * ih - pad,
        width: box.w * iw + 2 * pad,
        height: box.h * ih + 2 * pad,
        border: `4px solid ${line}`,
        borderRadius: 16,
        boxShadow: `0 0 0 ${8 * pulse}px ${soft}cc`,
        opacity: o,
        transform: `scale(${1.04 - 0.04 * inP})`,
      }}
    />
  );
};

// ---------------------------------------------------------------- overlays

export const Chip: React.FC<{
  at: number;
  until?: number;
  x: number;
  y: number;
  tone?: Tone;
  size?: number;
  children: React.ReactNode;
  align?: "left" | "right";
}> = ({ at, until, x, y, tone = "primary", size = 30, children, align = "left" }) => {
  const shown = useIn(at, 0.5);
  const gone = useIn(until ?? Infinity, 0.4);
  const p = shown * (1 - gone);
  const [line, soft] = TONE[tone];
  return (
    <div
      style={{
        position: "absolute",
        [align === "left" ? "left" : "right"]: x,
        top: y,
        opacity: p,
        transform: `translateY(${(1 - p) * 18}px)`,
        background: C.surface,
        border: `2px solid ${line}`,
        boxShadow: `0 14px 40px rgba(19,32,27,0.18), inset 0 0 0 999px ${soft}66`,
        color: C.text,
        borderRadius: 18,
        padding: "16px 26px",
        fontFamily: sans,
        fontSize: size,
        fontWeight: 500,
        maxWidth: 820,
        lineHeight: 1.3,
      }}
    >
      {children}
    </div>
  );
};

export const Captions: React.FC<{ captions: Caption[] }> = ({ captions }) => {
  const t = useT();
  const line = captions.find((c) => t >= c.start - 0.05 && t < c.end + 0.15);
  if (!line) return null;
  const o = interpolate(t, [line.start - 0.05, line.start + 0.1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 30 }}>
      <div
        style={{
          background: "rgba(19,32,27,0.9)",
          color: "#f3f4ef",
          fontFamily: sans,
          fontSize: 34,
          fontWeight: 500,
          padding: "12px 30px",
          borderRadius: 14,
          maxWidth: 1560,
          textAlign: "center",
          opacity: o,
          lineHeight: 1.3,
        }}
      >
        {line.text}
      </div>
    </AbsoluteFill>
  );
};

export const Backdrop: React.FC = () => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(1200px 600px at 85% -10%, #f6e7c4 0%, rgba(246,231,196,0) 60%),
                   linear-gradient(180deg, #eef1ea 0%, ${C.bg} 55%, #e6ece5 100%)`,
    }}
  />
);

/** The site's mark: a ring around a check. */
export const Mark: React.FC<{ size: number; color?: string }> = ({ size, color = C.primary }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="21" stroke={color} strokeWidth="3" />
    <circle cx="24" cy="24" r="14" stroke={color} strokeWidth="3" />
    <path d="M18 24.5l4.2 4.2L30.5 20" stroke={color} strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

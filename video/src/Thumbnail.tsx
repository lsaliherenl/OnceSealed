import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { Mark } from "./components";
import { C, mono, sans } from "./theme";

// YouTube cover (1280x720): the claim on the left, the real public record of retirement #3 on the right.

const MINT = "#8fd3b4";
// the record card in shots/07-verify.png, as fractions of the image
const CARD = { x: 0.156, y: 0.504, w: 0.417, h: 0.486 };
const CARD_W = 500;

export const Thumbnail: React.FC = () => {
  const imgW = CARD_W / CARD.w;
  const imgH = imgW / 1.5;
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(900px 500px at 90% 0%, #2c4a3d 0%, rgba(44,74,61,0) 70%), ${C.strip}`,
        fontFamily: sans,
      }}
    >
      <div style={{ position: "absolute", left: 70, top: 58, display: "flex", alignItems: "center", gap: 18 }}>
        <Mark size={64} color={MINT} />
        <span style={{ fontSize: 44, fontWeight: 600, color: "#f3f4ef", letterSpacing: -1 }}>OnceSealed</span>
      </div>
      <div
        style={{
          position: "absolute",
          left: 70,
          top: 170,
          fontSize: 84,
          fontWeight: 700,
          lineHeight: 1.04,
          letterSpacing: -3,
          color: "#f3f4ef",
        }}
      >
        Retired once.
        <br />
        <span style={{ color: MINT }}>Buyer sealed.</span>
        <br />
        Open to check.
      </div>
      <div style={{ position: "absolute", left: 70, top: 500, fontSize: 30, color: C.stripFg, width: 600, lineHeight: 1.35 }}>
        Carbon credit retirement that is private for the buyer and auditable by anyone
      </div>
      <div
        style={{
          position: "absolute",
          left: 70,
          bottom: 46,
          fontFamily: mono,
          fontSize: 22,
          color: MINT,
          letterSpacing: 1,
        }}
      >
        SEPOLIA TESTNET · REAL VERRA PROJECTS · IEEE CLIMATECHAIN 2026
      </div>
      <div
        style={{
          position: "absolute",
          right: 50,
          top: 130,
          width: CARD_W,
          height: imgH * CARD.h,
          overflow: "hidden",
          borderRadius: 22,
          transform: "rotate(-2.5deg)",
          boxShadow: "0 40px 90px rgba(0,0,0,0.45)",
          border: `3px solid ${MINT}`,
        }}
      >
        <Img
          src={staticFile("shots/07-verify.png")}
          style={{ position: "absolute", width: imgW, height: imgH, left: -CARD.x * imgW, top: -CARD.y * imgH }}
        />
      </div>
    </AbsoluteFill>
  );
};

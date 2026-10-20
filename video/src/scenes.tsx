import { BadgeCheck, Building2, EyeOff, FileLock2, Fingerprint, KeyRound, Link2, Lock, ShieldCheck } from "lucide-react";
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { Chip, Kicker, Mark, Shot, useIn } from "./components";
import { C, mono, sans } from "./theme";
import { clamp01, useT } from "./timing";

// Image coordinates below are fractions (0-1) of each screenshot, read off the captures in public/shots.

const fade = (t: number, at: number, dur = 0.5) => clamp01((t - at) / dur);

// ---------------------------------------------------------------- 1. problem

const Problem: React.FC = () => {
  const t = useT();
  const value = interpolate(t, [10.3, 14.5], [0.4, 17.2], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // the chart draws in from its axis as the narration goes, fully open as "seventeen percent" is said
  const wipe = interpolate(t, [0.3, 13.5], [90, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const title = useIn(0, 0.7);
  const stat = useIn(6.0, 0.6);
  return (
    <AbsoluteFill>
      <Kicker>THE PROBLEM</Kicker>
      <div
        style={{
          position: "absolute",
          left: 160,
          top: 130,
          width: 560,
          fontFamily: sans,
          opacity: title,
          transform: `translateY(${(1 - title) * 16}px)`,
        }}
      >
        <div style={{ fontSize: 64, fontWeight: 600, lineHeight: 1.08, color: C.text, letterSpacing: -1 }}>
          Who retired this credit?
        </div>
        <div style={{ fontSize: 30, color: C.muted, marginTop: 22, lineHeight: 1.4 }}>
          More and more buyers would rather not say.
        </div>
      </div>
      <div style={{ position: "absolute", left: 160, top: 450, width: 560, fontFamily: sans, opacity: stat }}>
        <div style={{ fontSize: 168, fontWeight: 600, color: C.primary, letterSpacing: -6, lineHeight: 1 }}>
          {value.toFixed(1)}%
        </div>
        <div style={{ fontSize: 28, color: C.text, marginTop: 14, lineHeight: 1.4 }}>
          of retired tonnes explicitly marked “not disclosed”, “anonymous” or “private”:{" "}
          <b>0.4% up to 2018 → 17.2% in 2023–2026</b>
        </div>
        <div style={{ fontSize: 20, color: C.muted, marginTop: 16, lineHeight: 1.4 }}>
          Our count over CarbonPlan OffsetsDB (snapshot 2026-06-01), a conservative lower bound.
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 770,
          top: 150,
          width: 1000,
          height: 667,
          borderRadius: 24,
          overflow: "hidden",
          background: C.surface,
          boxShadow: "0 30px 80px rgba(19,32,27,0.16)",
          opacity: useIn(0.3, 0.6),
        }}
      >
        <Img
          src={staticFile("shots/11-anonymity-trend.png")}
          style={{ width: "100%", height: "100%", clipPath: `inset(0 ${wipe}% 0 0)` }}
        />
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 2. tension

const Side: React.FC<{ at: number; icon: React.ReactNode; title: string; body: string; color: string; dim: number }> = ({
  at,
  icon,
  title,
  body,
  color,
  dim,
}) => {
  const p = useIn(at, 0.6);
  return (
    <div
      style={{
        width: 620,
        padding: "48px 52px",
        borderRadius: 28,
        background: C.surface,
        border: `2px solid ${color}`,
        boxShadow: "0 24px 60px rgba(19,32,27,0.12)",
        fontFamily: sans,
        opacity: p * dim,
        transform: `translateY(${(1 - p) * 24}px)`,
      }}
    >
      <div style={{ color }}>{icon}</div>
      <div style={{ fontSize: 50, fontWeight: 600, color: C.text, marginTop: 22 }}>{title}</div>
      <div style={{ fontSize: 28, color: C.muted, marginTop: 12, lineHeight: 1.4 }}>{body}</div>
    </div>
  );
};

const Tension: React.FC = () => {
  const t = useT();
  const both = useIn(10.4, 0.6);
  const or = fade(t, 7.0);
  return (
    <AbsoluteFill>
      <Kicker>THE TENSION</Kicker>
      <div style={{ position: "absolute", top: 210, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 70 }}>
        <Side
          at={7.2}
          icon={<EyeOff size={72} strokeWidth={1.6} />}
          title="Confidentiality"
          body="The buyer's identity is not published."
          color={C.seal}
          dim={1}
        />
        <div
          style={{
            alignSelf: "center",
            fontFamily: sans,
            fontSize: 44,
            fontWeight: 600,
            color: both > 0 ? C.primary : C.muted,
            opacity: or,
            width: 70,
            textAlign: "center",
          }}
        >
          {both > 0.5 ? "+" : "or"}
        </div>
        <Side
          at={0.4}
          icon={<BadgeCheck size={72} strokeWidth={1.6} />}
          title="Public proof"
          body="Each credit retired only once, quality claims backed by evidence."
          color={C.primary}
          dim={1}
        />
      </div>
      <div
        style={{
          position: "absolute",
          top: 690,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: both,
          transform: `scale(${0.94 + 0.06 * both})`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 22,
            background: C.strip,
            color: "#f3f4ef",
            borderRadius: 999,
            padding: "22px 46px",
            fontFamily: sans,
            fontSize: 44,
            fontWeight: 600,
          }}
        >
          <Mark size={52} color="#8fd3b4" /> OnceSealed gives both
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 3. overview

const Overview: React.FC = () => (
  <AbsoluteFill>
    <Kicker>THE IDEA</Kicker>
    <Shot
      src="01-overview.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.42, z: 1 },
        { at: 5.6, cx: 0.48, cy: 0.74, z: 1.12 },
      ]}
      boxes={[
        { from: 7.1, x: 0.156, y: 0.575, w: 0.243, h: 0.375 },
        { from: 7.7, x: 0.413, y: 0.575, w: 0.244, h: 0.375, tone: "seal" },
        { from: 8.4, x: 0.67, y: 0.575, w: 0.243, h: 0.375 },
      ]}
    />
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 4. once

const Once: React.FC = () => (
  <AbsoluteFill>
    <Kicker>1 · ONCE · NO DOUBLE COUNTING</Kicker>
    <Shot
      src="14-overlap.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.4, z: 1 },
        { at: 3.4, cx: 0.37, cy: 0.72, z: 1.5 },
        { at: 6.4, cx: 0.74, cy: 0.42, z: 1.55 },
        { at: 11.6, cx: 0.5, cy: 0.45, z: 1.02 },
      ]}
      boxes={[
        { from: 4.2, to: 7.0, x: 0.175, y: 0.68, w: 0.26, h: 0.1 },
        { from: 7.4, x: 0.603, y: 0.274, w: 0.31, h: 0.307, tone: "bad" },
      ]}
    />
    <Chip at={9.6} x={200} y={640} align="right" tone="bad">
      Rejected before any transaction: <span style={{ fontFamily: mono }}>AlreadyRetired(#1)</span>
    </Chip>
    <Chip at={12.4} x={200} y={760} align="right">
      No transfer · no mint · never a token <span style={{ color: C.muted }}>(Verra, 2022)</span>
    </Chip>
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 5. scale

const Scale: React.FC = () => (
  <AbsoluteFill>
    <Kicker>1 · ONCE · AT REAL SCALE</Kicker>
    <Shot
      src="12-scale-gas.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.5, z: 1 },
        { at: 6.0, cx: 0.32, cy: 0.33, z: 1.45 },
        { at: 12.6, cx: 0.5, cy: 0.62, z: 1 },
      ]}
      boxes={[
        { from: 8.8, to: 12.6, x: 0.275, y: 0.285, w: 0.32, h: 0.04, tone: "bad" },
        { from: 13.2, x: 0.105, y: 0.74, w: 0.5, h: 0.035 },
      ]}
    />
    <Chip at={0.8} until={5.8} x={200} y={130} align="right" size={26}>
      38,382 real retirements of one vintage (OffsetsDB), replayed on a local chain
    </Chip>
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 6. sealed

const Card: React.FC<{ at: number; x: number; y: number; w: number; title: string; icon: React.ReactNode; tone: string; children: React.ReactNode }> = ({
  at,
  x,
  y,
  w,
  title,
  icon,
  tone,
  children,
}) => {
  const p = useIn(at, 0.6);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        padding: "30px 34px",
        borderRadius: 24,
        background: C.surface,
        border: `2px solid ${tone}`,
        boxShadow: "0 20px 50px rgba(19,32,27,0.12)",
        fontFamily: sans,
        opacity: p,
        transform: `translateY(${(1 - p) * 20}px)`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14, color: tone, fontSize: 30, fontWeight: 600 }}>
        {icon}
        <span style={{ color: C.text }}>{title}</span>
      </div>
      <div style={{ marginTop: 16, fontSize: 25, color: C.muted, lineHeight: 1.45 }}>{children}</div>
    </div>
  );
};

const Arrow: React.FC<{ at: number; x: number; y: number; w: number; label?: string }> = ({ at, x, y, w, label }) => {
  const p = useIn(at, 0.6);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, opacity: p ? 1 : 0, fontFamily: mono }}>
      <div style={{ height: 4, width: `${p * 100}%`, background: C.primary, borderRadius: 2 }} />
      <div
        style={{
          position: "absolute",
          right: -2,
          top: -9,
          width: 0,
          height: 0,
          borderTop: "11px solid transparent",
          borderBottom: "11px solid transparent",
          borderLeft: `18px solid ${C.primary}`,
          opacity: p > 0.95 ? 1 : 0,
        }}
      />
      {label && <div style={{ fontSize: 20, color: C.muted, marginTop: 10, textAlign: "center", opacity: p }}>{label}</div>}
    </div>
  );
};

const FORMULA = "commitment = keccak256(abi.encode(buyerId, salt, batchId, start, end))";

const Sealed: React.FC = () => {
  const t = useT();
  const typed = Math.floor(FORMULA.length * clamp01((t - 0.2) / 2.6));
  return (
    <AbsoluteFill>
      <Kicker>2 · SEALED · PRIVATE, BUT AUDITABLE</Kicker>
      <div
        style={{
          position: "absolute",
          left: 160,
          top: 110,
          width: 1600,
          padding: "26px 36px",
          borderRadius: 20,
          background: C.strip,
          color: "#dce6e1",
          fontFamily: mono,
          fontSize: 34,
        }}
      >
        {FORMULA.slice(0, typed)}
        <span style={{ opacity: t < 3 && Math.floor(t * 2) % 2 === 0 ? 1 : 0 }}>▍</span>
      </div>
      <Card at={0.4} x={160} y={330} w={420} title="Buyer" icon={<Building2 size={36} />} tone={C.text}>
        Legal Entity Identifier (LEI)
        <br />
        <span style={{ fontFamily: mono, fontSize: 22 }}>fictional demo company</span>
      </Card>
      <Arrow at={2.2} x={600} y={420} w={200} label="+ random salt" />
      <Card at={3.0} x={820} y={330} w={420} title="Commitment" icon={<Fingerprint size={36} />} tone={C.primary}>
        Bound to the exact serial range: a revealed salt proves only this retirement.
      </Card>
      <Arrow at={4.4} x={1260} y={420} w={70} />
      <Card at={4.8} x={1350} y={330} w={410} title="On-chain" icon={<Link2 size={36} />} tone={C.primary}>
        Project · serial range · commitment · vault hash
        <br />
        <b style={{ color: C.seal }}>Buyer: sealed, no name</b>
      </Card>
      <Arrow at={6.6} x={600} y={720} w={200} label="encrypted" />
      <Card at={6.4} x={160} y={630} w={420} title="Vault" icon={<FileLock2 size={36} />} tone={C.seal}>
        LEI + salt, off-chain
      </Card>
      <Card at={8.6} x={820} y={630} w={940} title="Only the accredited auditor can open it" icon={<KeyRound size={36} />} tone={C.seal}>
        Sealed box to the auditor&apos;s public key; only the vault&apos;s hash goes on-chain. Not zero-knowledge:
        a hash commitment plus encryption.
      </Card>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 7. auditor

const Auditor: React.FC = () => (
  <AbsoluteFill>
    <Kicker>2 · SEALED · THE AUDITOR</Kicker>
    <Shot
      src="08-auditor.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.45, z: 1 },
        { at: 0.4, cx: 0.64, cy: 0.52, z: 1.35 },
        { at: 4.6, cx: 0.64, cy: 0.62, z: 1.55 },
      ]}
      boxes={[
        { from: 0.8, to: 4.6, x: 0.391, y: 0.55, w: 0.503, h: 0.115, tone: "seal" },
        { from: 3.0, x: 0.838, y: 0.302, w: 0.056, h: 0.026 },
        { from: 5.4, x: 0.391, y: 0.689, w: 0.503, h: 0.049 },
      ]}
    />
    <Chip at={2.0} until={5.0} x={200} y={770} align="right" size={24}>
      Six checks: vault hash · vault opens · range · LEI valid · LEI ↔ buyer id · commitment
    </Chip>
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 8. verify

const Verify: React.FC = () => (
  <AbsoluteFill>
    <Kicker>PUBLIC VERIFICATION · NO ACCOUNT NEEDED</Kicker>
    <Shot
      src="07-verify.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.35, z: 1 },
        { at: 1.6, cx: 0.33, cy: 0.3, z: 1.5 },
        { at: 4.8, cx: 0.37, cy: 0.74, z: 1.45 },
        { at: 7.2, cx: 0.75, cy: 0.62, z: 1.5 },
        { at: 11.4, cx: 0.5, cy: 0.55, z: 1 },
      ]}
      boxes={[
        { from: 2.2, to: 5.0, x: 0.156, y: 0.238, w: 0.28, h: 0.09 },
        { from: 5.6, to: 7.4, x: 0.17, y: 0.845, w: 0.27, h: 0.028, tone: "seal" },
        { from: 5.6, to: 7.4, x: 0.447, y: 0.558, w: 0.108, h: 0.025 },
        { from: 7.8, to: 11.6, x: 0.59, y: 0.504, w: 0.323, h: 0.295 },
      ]}
    />
    <Chip at={11.9} x={200} y={720} align="right" tone="seal">
      Commitment + encryption · not zero-knowledge
    </Chip>
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 9. evidence

const Evidence: React.FC = () => (
  <AbsoluteFill>
    <Kicker>3 · EVIDENCE-BACKED QUALITY</Kicker>
    <Shot
      src="02-project-quality.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.3, z: 1 },
        { at: 3.4, cx: 0.53, cy: 0.74, z: 1.12 },
      ]}
      boxes={[
        { from: 4.0, x: 0.157, y: 0.662, w: 0.757, h: 0.18 },
        { from: 9.0, x: 0.567, y: 0.684, w: 0.19, h: 0.07, tone: "seal" },
      ]}
    />
    <Chip at={1.4} x={200} y={130} align="right">
      11 real Verra projects
    </Chip>
    <Chip at={6.0} x={200} y={226} align="right">
      18 yes/no checks per project
    </Chip>
    <Chip at={8.9} x={200} y={322} align="right">
      5 ICVCM Core Carbon Principles
    </Chip>
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 10. citations

const Citations: React.FC = () => {
  const t = useT();
  const second = fade(t, 4.2, 0.6);
  return (
    <AbsoluteFill>
      <Kicker>3 · EVERY “FOUND” CITES A PARAGRAPH</Kicker>
      <Shot
        src="04-report-checks.png"
        keys={[
          { at: 0, cx: 0.5, cy: 0.3, z: 1 },
          { at: -0.2, cx: 0.63, cy: 0.53, z: 1.5 },
        ]}
        boxes={[
          { from: 0.6, x: 0.373, y: 0.428, w: 0.524, h: 0.147 },
          { from: 2.8, x: 0.393, y: 0.545, w: 0.3, h: 0.022, tone: "seal" },
        ]}
        opacity={1 - second}
      />
      {second > 0 && (
        <Shot
          src="10-review.png"
          offset={4.2}
          keys={[
            { at: 0, cx: 0.5, cy: 0.4, z: 1.1 },
            { at: 0.4, cx: 0.45, cy: 0.52, z: 1.3 },
          ]}
          boxes={[
            { from: 0.8, x: 0.17, y: 0.476, w: 0.3, h: 0.024, tone: "seal" },
            { from: 2.8, x: 0.17, y: 0.568, w: 0.73, h: 0.052 },
          ]}
          opacity={second}
        />
      )}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 11. data checks

const DataChecks: React.FC = () => (
  <AbsoluteFill>
    <Kicker>3 · DATA CHECKS · NO AI</Kicker>
    <Shot
      src="05-data-checks.png"
      keys={[
        { at: 0, cx: 0.5, cy: 0.3, z: 1 },
        { at: 3.6, cx: 0.5, cy: 0.27, z: 1.35 },
      ]}
      boxes={[{ from: 4.2, x: 0.157, y: 0.212, w: 0.757, h: 0.12, tone: "warn" }]}
    />
    <Chip at={5.0} x={200} y={600} align="right" tone="warn">
      Cordillera Azul (VCS985), 2009–2018: issued 27.1M t vs the document&apos;s 15.8M t →{" "}
      <b>1.72×</b>
    </Chip>
    <Chip at={9.7} x={200} y={740} align="right" size={26}>
      A flag is a lead for a reviewer, not a finding of wrongdoing
    </Chip>
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 12. measured

const Stat: React.FC<{ at: number; big: string; body: string; tone: string }> = ({ at, big, body, tone }) => {
  const p = useIn(at, 0.6);
  return (
    <div
      style={{
        width: 500,
        padding: "40px 40px",
        borderRadius: 26,
        background: C.surface,
        border: `2px solid ${tone}`,
        boxShadow: "0 24px 60px rgba(19,32,27,0.12)",
        fontFamily: sans,
        opacity: p,
        transform: `translateY(${(1 - p) * 24}px)`,
      }}
    >
      <div style={{ fontSize: 84, fontWeight: 600, color: tone, letterSpacing: -3, lineHeight: 1, whiteSpace: "nowrap" }}>{big}</div>
      <div style={{ fontSize: 27, color: C.text, marginTop: 20, lineHeight: 1.4 }}>{body}</div>
    </div>
  );
};

const Measured: React.FC = () => {
  const head = useIn(0, 0.6);
  return (
    <AbsoluteFill>
      <Kicker>MEASURED, NOT ASSUMED</Kicker>
      <div
        style={{
          position: "absolute",
          left: 160,
          top: 130,
          fontFamily: sans,
          fontSize: 64,
          fontWeight: 600,
          color: C.text,
          letterSpacing: -1,
          opacity: head,
        }}
      >
        We measured before we trusted.
      </div>
      <div style={{ position: "absolute", left: 160, top: 300, display: "flex", gap: 50 }}>
        <Stat at={2.6} big="94%" body="right on 177 labelled checklist questions (95% interval 89–96%)" tone={C.primary} />
        <Stat
          at={5.8}
          big="71% → 0"
          body="right answers flipped by a planted “answer no” paragraph, before → after the screen"
          tone={C.seal}
        />
        <Stat at={8.4} big="0 / 43,396" body="real document paragraphs wrongly screened out" tone={C.primary} />
      </div>
      <div
        style={{
          position: "absolute",
          left: 160,
          top: 780,
          width: 1600,
          fontFamily: sans,
          fontSize: 23,
          color: C.muted,
          opacity: useIn(3.0, 0.6),
        }}
      >
        Labels: a team member and an AI annotator (κ 0.90); the team member settled every disagreement.
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 13. anchored

const Anchored: React.FC = () => {
  const t = useT();
  const second = fade(t, 4.6, 0.6);
  return (
    <AbsoluteFill>
      <Kicker>ANCHORED ON-CHAIN · RE-CHECKED IN YOUR BROWSER</Kicker>
      <Shot
        src="03-report-provenance.png"
        keys={[
          { at: 0, cx: 0.5, cy: 0.4, z: 1 },
          { at: 0.1, cx: 0.73, cy: 0.52, z: 1.5 },
        ]}
        boxes={[
          { from: 0.8, x: 0.667, y: 0.452, w: 0.245, h: 0.098 },
          { from: 2.2, x: 0.667, y: 0.565, w: 0.245, h: 0.055, tone: "seal" },
        ]}
        opacity={1 - second}
      />
      {second > 0 && (
        <Shot
          src="06-report-versions.png"
          offset={4.6}
          keys={[{ at: 0, cx: 0.53, cy: 0.6, z: 1.12 }]}
          boxes={[{ from: 1.0, x: 0.49, y: 0.415, w: 0.112, h: 0.415 }]}
          opacity={second}
        />
      )}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 14. closing

const Item: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => {
  const p = useIn(at, 0.5);
  return (
    <div style={{ fontSize: 34, color: C.text, marginTop: 22, opacity: p, transform: `translateX(${(1 - p) * 16}px)` }}>
      {children}
    </div>
  );
};

const Closing: React.FC = () => {
  const t = useT();
  const end = fade(t, 10.2, 0.8);
  const columns = 1 - end;
  const tag = (at: number) => clamp01((t - at) / 0.6);
  const real = useIn(0, 0.5);
  const simulated = useIn(5.2, 0.5);
  const signal = useIn(8.1, 0.5);
  return (
    <AbsoluteFill style={{ fontFamily: sans }}>
      {columns > 0 && (
        <AbsoluteFill style={{ opacity: columns }}>
          <Kicker>HONEST ABOUT WHAT IS REAL</Kicker>
          <div style={{ position: "absolute", left: 160, top: 150, display: "flex", gap: 60 }}>
            <div style={{ width: 770 }}>
              <div style={{ fontSize: 52, fontWeight: 600, color: C.primary, opacity: real }}>Real</div>
              <Item at={1.0}>Verra projects and their documents</Item>
              <Item at={2.6}>Issuance and retirement histories (OffsetsDB)</Item>
              <Item at={3.6}>Contract and transactions on Sepolia</Item>
            </div>
            <div style={{ width: 770 }}>
              <div style={{ fontSize: 52, fontWeight: 600, color: C.warn, opacity: simulated }}>Simulated</div>
              <Item at={6.7}>Serial numbers (SIM-…)</Item>
              <Item at={7.3}>Buyers: fictional companies</Item>
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              left: 160,
              top: 640,
              width: 1600,
              padding: "26px 34px",
              borderRadius: 20,
              background: C.warnSoft,
              color: C.text,
              fontSize: 32,
              opacity: signal,
            }}
          >
            <b>Signal, not verdict.</b> The quality score shows where the documents evidence each principle; it is not
            an ICVCM assessment or a rating of the project.
          </div>
        </AbsoluteFill>
      )}
      {end > 0 && (
        <AbsoluteFill style={{ opacity: end, alignItems: "center", justifyContent: "center", paddingBottom: 90 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
            <Mark size={110} />
            <div style={{ fontSize: 124, fontWeight: 600, color: C.text, letterSpacing: -3 }}>OnceSealed</div>
          </div>
          <div style={{ display: "flex", gap: 34, marginTop: 34, fontSize: 40, fontWeight: 500 }}>
            <span style={{ opacity: tag(15.6), color: C.primary }}>
              <ShieldCheck size={36} style={{ verticalAlign: -5 }} /> Retired once.
            </span>
            <span style={{ opacity: tag(16.7), color: C.seal }}>
              <Lock size={36} style={{ verticalAlign: -5 }} /> Sealed for the buyer.
            </span>
            <span style={{ opacity: tag(18.6), color: C.text }}>
              <BadgeCheck size={36} style={{ verticalAlign: -5 }} /> Open for anyone to check.
            </span>
          </div>
          <div
            style={{
              marginTop: 70,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 14,
              fontFamily: mono,
              fontSize: 28,
              color: C.muted,
              opacity: tag(10.6),
            }}
          >
            <span style={{ color: C.primary, fontSize: 34 }}>once-sealed.vercel.app</span>
            <span>github.com/lsaliherenl/OnceSealed</span>
            <span>Sepolia · 0xBb88057576b92Ef27753A6b2a4Df83bE444F1308 · verified on Etherscan</span>
          </div>
          <div style={{ position: "absolute", bottom: 120, fontSize: 22, color: C.muted, opacity: tag(12.7) }}>
            IEEE ClimateChain Global Hackathon 2026 · prototype on a public testnet · MIT licence
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

export const SCENE_VIEWS: Record<string, React.FC> = {
  problem: Problem,
  tension: Tension,
  overview: Overview,
  once: Once,
  scale: Scale,
  sealed: Sealed,
  auditor: Auditor,
  verify: Verify,
  evidence: Evidence,
  citations: Citations,
  datachecks: DataChecks,
  measured: Measured,
  anchored: Anchored,
  closing: Closing,
};


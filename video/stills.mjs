// Render check frames: node stills.mjs <scene>:<seconds> ...  → out/stills/<scene>-<seconds>.png
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";

const narration = JSON.parse(fs.readFileSync("src/narration.generated.json", "utf8"));
const FPS = 30, LEAD = 0.4, TAIL = 0.5, EXTRA = { closing: 3.5 };
const start = {};
let f = 0;
for (const s of narration.scenes) {
  start[s.id] = f;
  f += Math.ceil((LEAD + s.duration + TAIL + (EXTRA[s.id] ?? 0)) * FPS);
}
const browserExecutable = process.env.BROWSER ?? null;
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id: "OnceSealed", browserExecutable });
fs.mkdirSync("out/stills", { recursive: true });
for (const arg of process.argv.slice(2)) {
  const [id, sec] = arg.split(":");
  const frame = start[id] + Math.round((LEAD + Number(sec)) * FPS);
  const output = `out/stills/${id}-${sec}.png`;
  await renderStill({ serveUrl, composition, frame, output, browserExecutable, scale: 0.5 });
  console.log(output);
}

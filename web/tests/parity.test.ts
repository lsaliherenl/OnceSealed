/**
 * Browser ↔ Python parity: the hashing the verification and report pages run in the browser
 * (src/lib/hashing.ts) must give exactly what the Python code gives. The expected values come from
 * tests/vectors.json (written by scripts/gen_vectors.py with the Python functions, also checked by
 * pytest and Foundry) and from the published reports, whose hashes Python computed and Sepolia holds.
 *
 *   npm test
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import type { Hex } from "viem";
import { buyerId, canonicalJson, commitment, isValidLei, receiptCommitment, reportHash, textId } from "../src/lib/hashing.ts";

const ROOT = new URL("../../", import.meta.url);
const read = (path: string) => readFileSync(new URL(path, ROOT), "utf-8");

/** JSON.parse that keeps integers above 2^53 exact (the uint64 vector), using the reviver's source text. */
const parseExact = (text: string) =>
  JSON.parse(text, ((_key: string, value: unknown, ctx: { source?: string }) =>
    typeof value === "number" && Number.isInteger(value) && !Number.isSafeInteger(value) ? BigInt(ctx.source!) : value) as never);

const V = parseExact(read("tests/vectors.json"));

test("text ids (project and batch ids)", () => {
  for (const v of V.text_ids) assert.equal(textId(v.text), v.id, v.text);
});

test("commitments, including a range near the uint64 maximum", () => {
  assert.equal(V.commitments.length, V.commitment_count);
  for (const v of V.commitments) {
    assert.equal(buyerId(v.lei), v.buyer_id);
    assert.equal(textId(v.batch_key), v.batch_id);
    assert.equal(commitment(v.buyer_id as Hex, v.salt as Hex, v.batch_id as Hex, v.start, v.end), v.commitment, v.batch_key);
  }
  assert.equal(typeof V.commitments[2].end, "bigint", "the uint64 vector must not be rounded by JSON.parse");
});

test("LEI validation agrees with is_valid_lei", () => {
  for (const v of V.lei_checks) assert.equal(isValidLei(v.lei), v.valid, JSON.stringify(v.lei));
});

test("buyer id normalises case and spaces as buyer_id does", () => {
  for (const v of V.buyer_ids) assert.equal(buyerId(v.input), v.buyer_id, JSON.stringify(v.input));
});

test("offline receipt check agrees with receipt_commitment", () => {
  for (const v of V.receipts) {
    if (v.error) assert.throws(() => receiptCommitment(v.receipt), v.name);
    else assert.equal(receiptCommitment(v.receipt), v.commitment, v.name);
  }
});

test("canonical JSON: floats, key order by code point, escapes, big integers", () => {
  for (const v of V.canonical_json) {
    assert.equal(canonicalJson(v.text), v.canonical);
    assert.equal(reportHash(v.text), v.hash);
  }
});

test("every published report hashes in the browser to the hash Python computed and Sepolia holds", () => {
  const site = JSON.parse(read("web/src/data/site.json"));
  const files = readdirSync(new URL("reports/", ROOT)).filter((f) => f.endsWith(".json"));
  assert.ok(files.length > 0);
  for (const f of files) {
    const id = f.replace(/\.json$/, "");
    const project = site.projects.find((p: { id: string }) => p.id === id);
    const text = read(`reports/${f}`);
    assert.equal(reportHash(text), project.report.hash, `${id}: browser hash vs scripts/export_web_data.py`);
    assert.equal(reportHash(text), project.anchors.at(-1).report_hash, `${id}: browser hash vs the latest anchor`);
    assert.equal(read(`web/public/reports/${f}`), text, `${id}: the copy the web app serves is the published file`);
  }
});

test("every archived report version hashes to the hash anchored for that version", () => {
  const site = JSON.parse(read("web/src/data/site.json"));
  let n = 0;
  for (const p of site.projects) {
    for (const a of p.anchors) {
      const text = read(`reports/history/${p.id}/v${a.version}.json`);
      assert.equal(reportHash(text), a.report_hash, `${p.id} v${a.version}`);
      assert.equal(read(`web/public${a.file}`), text, `${p.id} v${a.version}: served copy`);
      n++;
    }
  }
  assert.ok(n >= 37, `only ${n} archived versions`);
});

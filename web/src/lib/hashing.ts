/**
 * The hashing the browser shares with the Python code, kept free of app imports so the parity test
 * (web/tests/parity.test.ts) can run it under plain Node against tests/vectors.json:
 *
 *   textId, buyerId, isValidLei   core/privacy/identity.py
 *   commitment                    core/privacy/commitment.py and the contract's commitmentOf
 *   receiptCommitment             core/privacy/receipt.py receipt_commitment
 *   canonicalJson, reportHash     core/hashing.py (the report hash anchored on-chain)
 */
import { encodeAbiParameters, keccak256, toBytes, type Hex } from "viem";

/** Same as Web3.keccak(text=...) in core/privacy/identity.py. */
export const textId = (s: string): Hex => keccak256(toBytes(s));

const LEI_RE = /^[0-9A-Z]{18}[0-9]{2}$/;

/** ISO 17442: 20 characters, ISO 7064 mod 97-10 check digits. Strict, as `is_valid_lei`: no case or space folding. */
export function isValidLei(lei: string) {
  if (!LEI_RE.test(lei)) return false;
  const digits = [...lei].map((c) => (/[0-9]/.test(c) ? c : String(c.charCodeAt(0) - 55))).join("");
  return BigInt(digits) % BigInt(97) === BigInt(1);
}

/** keccak256("LEI:" + LEI) after trimming and upper-casing, as `buyer_id`; throws on an invalid LEI. */
export function buyerId(lei: string): Hex {
  const s = lei.trim().toUpperCase();
  if (!isValidLei(s)) throw new Error(`invalid LEI: ${JSON.stringify(lei)}`);
  return textId(`LEI:${s}`);
}

const UINT64_MAX = (BigInt(1) << BigInt(64)) - BigInt(1);

/** keccak256(abi.encode(buyerId, salt, batchId, start, end)), as `commitmentOf` in the contract. */
export function commitment(buyer: Hex, salt: Hex, batchId: Hex, start: number | bigint, end: number | bigint): Hex {
  const s = BigInt(start);
  const e = BigInt(end);
  if (s < BigInt(0) || s > e || e > UINT64_MAX) throw new Error(`invalid range ${s}-${e}`);
  return keccak256(
    encodeAbiParameters(
      [{ type: "bytes32" }, { type: "bytes32" }, { type: "bytes32" }, { type: "uint64" }, { type: "uint64" }],
      [buyer, salt, batchId, s, e],
    ),
  );
}

export type ReceiptFields = {
  batch_id: Hex;
  start: number | bigint;
  end: number | bigint;
  lei: string;
  buyer_id: Hex;
  salt: Hex;
};

/** The commitment a receipt opens to; throws when its LEI and buyer id do not match (as `receipt_commitment`). */
export function receiptCommitment(r: ReceiptFields): Hex {
  if (!isValidLei(r.lei) || buyerId(r.lei) !== r.buyer_id.toLowerCase()) {
    throw new Error("receipt LEI and buyer_id do not match");
  }
  return commitment(r.buyer_id, r.salt, r.batch_id, r.start, r.end);
}

/* ------------------------------------------------------------------ */
/* Canonical JSON, as core/hashing.py canonical_json:                  */
/* json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False) */
/* ------------------------------------------------------------------ */

/** Python sorts keys by code point; JavaScript's default sort compares UTF-16 units, which differs above U+FFFF. */
function byCodePoint(a: string, b: string) {
  const x = [...a];
  const y = [...b];
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = x[i].codePointAt(0)! - y[i].codePointAt(0)!;
    if (d !== 0) return d;
  }
  return x.length - y.length;
}

/** Python's float repr: shortest round-trip digits, fixed notation for exponents -4..15, at least one decimal. */
function pyFloat(x: number) {
  if (!Number.isFinite(x)) throw new Error("NaN and Infinity are not allowed in canonical JSON");
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const [mantissa, exp] = Math.abs(x).toExponential().split("e");
  const digits = mantissa.replace(".", "");
  const e = Number(exp);
  const sign = x < 0 ? "-" : "";
  if (e < -4 || e > 15) {
    const m = digits.length > 1 ? `${digits[0]}.${digits.slice(1)}` : digits;
    return `${sign}${m}e${e < 0 ? "-" : "+"}${String(Math.abs(e)).padStart(2, "0")}`;
  }
  if (e < 0) return `${sign}0.${"0".repeat(-e - 1)}${digits}`;
  const int = digits.slice(0, e + 1).padEnd(e + 1, "0");
  return `${sign}${int}.${digits.slice(e + 1) || "0"}`;
}

const NUMBER = /-?(?:0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?/y;

/**
 * Canonical form of a JSON text, reading numbers from the text itself: JSON.parse would turn 1.0 into 1 and
 * lose integers above 2^53, both of which Python keeps.
 */
export function canonicalJson(text: string): string {
  let i = 0;
  const fail = (what: string): never => {
    throw new SyntaxError(`${what} at position ${i}`);
  };
  const ws = () => {
    while (i < text.length && " \t\n\r".includes(text[i])) i++;
  };
  const string = (): string => {
    const start = i++;
    while (i < text.length) {
      if (text[i] === "\\") i += 2;
      else if (text[i++] === '"') return JSON.parse(text.slice(start, i));
    }
    return fail("unterminated string");
  };
  const value = (): string => {
    ws();
    const c = text[i];
    if (c === "{") {
      i++;
      const entries = new Map<string, string>();
      ws();
      if (text[i] === "}") {
        i++;
        return "{}";
      }
      for (;;) {
        ws();
        if (text[i] !== '"') fail("expected a key");
        const key = string();
        ws();
        if (text[i++] !== ":") fail("expected ':'");
        entries.set(key, value());
        ws();
        const d = text[i++];
        if (d === "}") break;
        if (d !== ",") fail("expected ',' or '}'");
      }
      const keys = [...entries.keys()].sort(byCodePoint);
      return `{${keys.map((k) => `${JSON.stringify(k)}:${entries.get(k)}`).join(",")}}`;
    }
    if (c === "[") {
      i++;
      const items: string[] = [];
      ws();
      if (text[i] === "]") {
        i++;
        return "[]";
      }
      for (;;) {
        items.push(value());
        ws();
        const d = text[i++];
        if (d === "]") break;
        if (d !== ",") fail("expected ',' or ']'");
      }
      return `[${items.join(",")}]`;
    }
    if (c === '"') return JSON.stringify(string());
    for (const literal of ["true", "false", "null"]) {
      if (text.startsWith(literal, i)) {
        i += literal.length;
        return literal;
      }
    }
    NUMBER.lastIndex = i;
    const m = NUMBER.exec(text);
    if (!m) return fail("unexpected character");
    i += m[0].length;
    if (m[1] || m[2]) return pyFloat(Number(m[0])); // Python reads it as a float
    return BigInt(m[0]).toString(); // an int, any size ("-0" becomes "0", as in Python)
  };
  const out = value();
  ws();
  if (i !== text.length) fail("unexpected data after the JSON value");
  return out;
}

/** keccak256 of the canonical JSON: the report hash the contract stores (core/hashing.py hash_json). */
export const reportHash = (text: string): Hex => keccak256(toBytes(canonicalJson(text)));

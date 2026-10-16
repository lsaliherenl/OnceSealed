/**
 * Browser-side reads of the RetirementRegistry on Sepolia, and the same hashing the Python code uses
 * (core/privacy/identity.py, commitment.py, receipt.py), so a receipt can be checked without our server.
 */
import {
  createPublicClient,
  encodeAbiParameters,
  fallback,
  http,
  keccak256,
  toBytes,
  type Hex,
} from "viem";
import { sepolia } from "viem/chains";
import { AUDIT_FROM_CHAIN, NETWORK, type AuditStatus } from "@/lib/data";
import { registryAbi } from "@/lib/registryAbi";

const RPC_URLS = [
  process.env.NEXT_PUBLIC_SEPOLIA_RPC_URL,
  "https://ethereum-sepolia-rpc.publicnode.com",
  sepolia.rpcUrls.default.http[0],
].filter((u): u is string => !!u);

export const client = createPublicClient({
  chain: sepolia,
  transport: fallback(RPC_URLS.map((u) => http(u, { retryCount: 1, timeout: 15_000 }))),
});

const contract = { address: NETWORK.contract, abi: registryAbi } as const;

/** Same as Web3.keccak(text=...) in core/privacy/identity.py. */
export const textId = (s: string): Hex => keccak256(toBytes(s));
export const buyerId = (lei: string): Hex => textId(`LEI:${lei.trim().toUpperCase()}`);

/** keccak256(abi.encode(buyerId, salt, batchId, start, end)), as `commitmentOf` in the contract. */
export function commitment(buyer: Hex, salt: Hex, batchId: Hex, start: number, end: number): Hex {
  return keccak256(
    encodeAbiParameters(
      [{ type: "bytes32" }, { type: "bytes32" }, { type: "bytes32" }, { type: "uint64" }, { type: "uint64" }],
      [buyer, salt, batchId, BigInt(start), BigInt(end)],
    ),
  );
}

/** ISO 17442: 20 alphanumerics, ISO 7064 mod 97-10 check digits. */
export function isValidLei(lei: string) {
  const s = lei.trim().toUpperCase();
  if (!/^[A-Z0-9]{18}[0-9]{2}$/.test(s)) return false;
  const digits = [...s].map((c) => (/[0-9]/.test(c) ? c : String(c.charCodeAt(0) - 55))).join("");
  return BigInt(digits) % BigInt(97) === BigInt(1);
}

export type OnchainRetirement = {
  id: number;
  batchId: Hex;
  start: number;
  end: number;
  buyerCommitment: Hex;
  auditVaultHash: Hex;
  reportVersion: number;
  retiredAt: Date;
  audit: AuditStatus;
};

export async function retirementCount() {
  return Number(await client.readContract({ ...contract, functionName: "retirementCount" }));
}

export async function getRetirement(id: number): Promise<OnchainRetirement> {
  const r = await client.readContract({ ...contract, functionName: "getRetirement", args: [BigInt(id)] });
  return {
    id,
    batchId: r.batchId,
    start: Number(r.start),
    end: Number(r.end),
    buyerCommitment: r.buyerCommitment,
    auditVaultHash: r.auditVaultHash,
    reportVersion: Number(r.reportVersion),
    retiredAt: new Date(Number(r.retiredAt) * 1000),
    audit: AUDIT_FROM_CHAIN[Number(r.audit)],
  };
}

/**
 * Retirement id covering a serial, 0 if none. Every batch on the Sepolia deployment uses standard lots,
 * where the contract answers in constant time. For free-range batches at scale, build the answer from
 * CreditRetired events instead (as core/chain/registry.py does).
 */
export async function retirementOf(batchId: Hex, serial: number) {
  return Number(await client.readContract({ ...contract, functionName: "retirementOf", args: [batchId, BigInt(serial)] }));
}

export async function latestReport(projectId: string) {
  const count = await client.readContract({ ...contract, functionName: "reportCount", args: [textId(projectId)] });
  if (count === 0) return null;
  const r = await client.readContract({ ...contract, functionName: "latestReport", args: [textId(projectId)] });
  return { version: Number(count), reportHash: r.reportHash, methodHash: r.methodHash, score: Number(r.score) };
}

export async function verifyClaim(id: number, buyer: Hex, salt: Hex) {
  return client.readContract({ ...contract, functionName: "verifyClaim", args: [BigInt(id), buyer, salt] });
}

/** Transactions that recorded and attested a retirement (from its events). */
export async function retirementTxs(id: number) {
  const fromBlock = BigInt(NETWORK.deploy_block);
  const [retired, attested] = await Promise.all([
    client.getContractEvents({ ...contract, eventName: "CreditRetired", args: { retirementId: BigInt(id) }, fromBlock }),
    client.getContractEvents({ ...contract, eventName: "RetirementAttested", args: { retirementId: BigInt(id) }, fromBlock }),
  ]);
  return { retireTx: retired[0]?.transactionHash, attestTx: attested[0]?.transactionHash };
}

/* ------------------------------------------------------------------ */
/* Receipt check (mirrors OnceSealed.verify_receipt in core/service.py) */
/* ------------------------------------------------------------------ */

type Receipt = {
  version?: string;
  retirement_id: number;
  chain_id: number;
  contract: string;
  batch_id: Hex;
  start: number;
  end: number;
  lei: string;
  buyer_id: Hex;
  salt: Hex;
};

export type LotCheck = {
  retirementId: number;
  start: number;
  end: number;
  batchId: Hex;
  checks: Record<string, boolean>;
  audit: AuditStatus | null;
  error?: string;
};

export type ReceiptCheck = {
  valid: boolean;
  lei: string;
  quantity: number;
  lots: LotCheck[];
  bundleChecks: Record<string, boolean>;
  audit: AuditStatus | null;
  error?: string;
};

export const RECEIPT_CHECKS: Record<string, string> = {
  same_chain_and_contract: "Receipt names this chain and contract",
  range_matches_chain: "Batch and serial range match the on-chain record",
  receipt_matches_commitment: "Commitment opens: LEI and salt recompute the on-chain commitment",
  contract_verify_claim: "The contract's verifyClaim view returns true",
  same_buyer_in_all_lots: "Every lot names the same buyer",
};

async function checkLot(r: Receipt): Promise<LotCheck> {
  const out: LotCheck = { retirementId: Number(r.retirement_id), start: r.start, end: r.end, batchId: r.batch_id, checks: {}, audit: null };
  try {
    out.checks.same_chain_and_contract =
      Number(r.chain_id) === NETWORK.chain_id && r.contract.toLowerCase() === NETWORK.contract.toLowerCase();
    const rec = await getRetirement(Number(r.retirement_id));
    out.audit = rec.audit;
    out.checks.range_matches_chain =
      r.batch_id.toLowerCase() === rec.batchId.toLowerCase() && r.start === rec.start && r.end === rec.end;
    const leiOk = isValidLei(r.lei) && buyerId(r.lei) === r.buyer_id.toLowerCase();
    out.checks.receipt_matches_commitment =
      leiOk && commitment(r.buyer_id, r.salt, r.batch_id, r.start, r.end) === rec.buyerCommitment.toLowerCase();
    out.checks.contract_verify_claim = await verifyClaim(Number(r.retirement_id), r.buyer_id, r.salt);
  } catch (e) {
    out.error = e instanceof Error ? e.message.split("\n")[0] : String(e);
  }
  return out;
}

const worst = (statuses: (AuditStatus | null)[]): AuditStatus | null =>
  statuses.includes("rejected") ? "rejected" : statuses.includes(null) ? null : statuses.includes("pending") ? "pending" : "verified";

const lotValid = (l: LotCheck) => !l.error && Object.keys(l.checks).length === 4 && Object.values(l.checks).every(Boolean);

/** Checks a receipt-v1 or receipt-bundle-v1 file against the chain. */
export async function checkReceipt(json: unknown): Promise<ReceiptCheck> {
  const doc = json as Partial<Receipt> & { lots?: Receipt[]; lei?: string };
  const isBundle = Array.isArray(doc?.lots);
  const receipts: Receipt[] = isBundle ? doc.lots! : doc && "retirement_id" in doc ? [doc as Receipt] : [];
  if (receipts.length === 0) {
    return { valid: false, lei: "", quantity: 0, lots: [], bundleChecks: {}, audit: null, error: "Not a OnceSealed receipt." };
  }
  const lots = await Promise.all(receipts.map(checkLot));
  const bundleChecks: Record<string, boolean> = {};
  if (isBundle) {
    bundleChecks.same_buyer_in_all_lots = receipts.every((r) => String(r.lei).toUpperCase() === String(doc.lei).toUpperCase());
  }
  const valid = lots.every(lotValid) && Object.values(bundleChecks).every(Boolean);
  return {
    valid,
    lei: String(isBundle ? doc.lei : receipts[0].lei).toUpperCase(),
    quantity: receipts.reduce((n, r) => n + r.end - r.start + 1, 0),
    lots,
    bundleChecks,
    audit: worst(lots.map((l) => l.audit)),
  };
}

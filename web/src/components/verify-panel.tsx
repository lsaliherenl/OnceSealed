"use client";

import { Check, FileText, LoaderCircle, Lock, Search, TriangleAlert, Upload, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EtherscanLink, HashChip } from "@/components/hash";
import { TransitionLink } from "@/components/transition-link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout, Card, Eyebrow, KeyValue } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import {
  RECEIPT_CHECKS,
  type OnchainRetirement,
  type ReceiptCheck,
  checkReceipt,
  getRetirement,
  retirementCount,
  retirementOf,
  retirementTxs,
} from "@/lib/chain";
import { AUDIT_LABEL, type AuditStatus, buyerName, parseSerial, projectOfBatch, rangeLabel } from "@/lib/data";
import { cn, formatInt, staggerStyle } from "@/lib/utils";

type Mode = "id" | "serial";

type Lookup =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "free"; serial: string }
  | { kind: "found"; record: OnchainRetirement; serial?: string; retireTx?: string; attestTx?: string };

const errorText = (e: unknown) => (e instanceof Error ? e.message.split("\n")[0] : String(e));

/** Reads a retirement by number, or the retirement covering a serial, straight from the contract. */
async function lookupOnChain(m: Mode, value: string): Promise<Lookup> {
  try {
    let id: number;
    let serial: string | undefined;
    if (m === "serial") {
      const parsed = parseSerial(value);
      if (!parsed) return { kind: "error", message: "Unknown serial. Use the form SIM-VCS1477-2015-001-000001500." };
      id = await retirementOf(parsed.batch.batch_id, parsed.serial);
      serial = value.trim().toUpperCase();
      if (id === 0) return { kind: "free", serial };
    } else {
      id = parseInt(value.replace(/^#/, ""), 10);
      const count = await retirementCount();
      if (!Number.isFinite(id) || id < 1 || id > count) {
        return { kind: "error", message: `No retirement #${value}. The contract holds ${count} retirements so far.` };
      }
    }
    const [record, txs] = await Promise.all([
      getRetirement(id),
      retirementTxs(id).catch(() => ({ retireTx: undefined, attestTx: undefined })),
    ]);
    return { kind: "found", record, serial, ...txs };
  } catch (e) {
    return { kind: "error", message: `Could not read the contract: ${errorText(e)}` };
  }
}

/** The lookup box in the top bar sends ?q=1 or ?q=SIM-…; a new query remounts the panel. */
export function VerifyPanel() {
  const q = useSearchParams().get("q") ?? "";
  return <VerifyPanelFor key={q} q={q} />;
}

function VerifyPanelFor({ q }: { q: string }) {
  const initialMode: Mode = q && !/^#?\d+$/.test(q) ? "serial" : "id";
  const [mode, setMode] = useState<Mode>(initialMode);
  const [qId, setQId] = useState(initialMode === "id" && q ? q.replace(/^#/, "") : "1");
  const [qSerial, setQSerial] = useState(initialMode === "serial" ? q : "SIM-VCS1477-2015-001-000001500");
  const [lookup, setLookup] = useState<Lookup>({ kind: "loading" });
  const [file, setFile] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<ReceiptCheck | "checking" | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    let live = true;
    lookupOnChain(initialMode, initialMode === "serial" ? q : q || "1").then((r) => live && setLookup(r));
    return () => {
      live = false;
    };
  }, [initialMode, q]);

  const run = (m: Mode, value: string) => {
    setLookup({ kind: "loading" });
    void lookupOnChain(m, value).then(setLookup);
  };

  const readFile = async (f: File | undefined) => {
    if (!f) return;
    setFile(f.name);
    setReceipt("checking");
    try {
      setReceipt(await checkReceipt(JSON.parse(await f.text())));
    } catch (e) {
      setReceipt({ valid: false, lei: "", quantity: 0, lots: [], bundleChecks: {}, audit: null, error: `Could not read the file: ${errorText(e)}` });
    }
  };

  const query = mode === "serial" ? qSerial : qId;

  return (
    <>
      <Card className="px-6 py-5">
        <form
          role="search"
          className="flex flex-wrap items-end gap-x-5 gap-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            run(mode, query);
          }}
        >
          <div className="flex flex-col gap-2">
            <span id="mode-l" className="text-[13px] font-semibold">
              Look up by
            </span>
            <div role="group" aria-labelledby="mode-l" className="inline-flex gap-1 rounded-[10px] bg-secondary p-1">
              {(
                [
                  ["id", "Retirement #"],
                  ["serial", "Serial number"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={mode === value}
                  onClick={() => setMode(value)}
                  className="min-h-10 cursor-pointer rounded-[7px] px-3.5 text-sm font-semibold text-muted-foreground transition-[background-color,color,box-shadow] duration-300 aria-pressed:bg-card aria-pressed:text-foreground aria-pressed:shadow-sm"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-[1_1_320px] flex-col gap-2">
            <Label htmlFor="q" className="font-semibold text-foreground">
              {mode === "serial" ? "Serial number (simulated)" : "Retirement number"}
            </Label>
            <Input
              id="q"
              autoComplete="off"
              className="font-mono"
              value={query}
              onChange={(e) => (mode === "serial" ? setQSerial : setQId)(e.target.value)}
            />
          </div>
          <Button type="submit" variant="primary" disabled={lookup.kind === "loading"}>
            <Search aria-hidden />
            Look up
          </Button>
        </form>
      </Card>

      <div className="flex flex-wrap items-start gap-6">
        <Card className="flex min-w-0 flex-[1_1_560px] flex-col gap-[22px] p-7">
          <PublicRecord lookup={lookup} />
        </Card>

        <Card className="flex min-w-0 flex-[1_1_420px] flex-col gap-[18px] p-7">
          <section aria-labelledby="rc-h" className="contents">
            <div className="flex flex-col gap-1">
              <h2 id="rc-h" className="text-xl leading-snug font-semibold">
                Check a receipt
              </h2>
              <p className="text-sm text-muted-foreground">
                The file is read in this browser and never uploaded. Each lot is recomputed and checked against the
                contract.
              </p>
            </div>

            {file == null ? (
              <label
                key="drop"
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  void readFile(e.dataTransfer.files[0]);
                }}
                className={cn(
                  "animate-rise-fast relative flex min-h-[150px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-[1.5px] border-dashed border-input bg-secondary p-6 text-center transition-colors duration-300 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring hover:border-primary hover:bg-primary-soft",
                  dragging && "border-primary bg-primary-soft",
                )}
              >
                <input
                  type="file"
                  accept=".json,application/json"
                  className="sr-only"
                  onChange={(e) => void readFile(e.target.files?.[0])}
                />
                <Upload aria-hidden className="size-7 text-primary" />
                <span className="font-semibold">Drop a receipt file here</span>
                <span className="text-[13px] text-muted-foreground">or click to choose · receipt JSON</span>
              </label>
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-secondary px-3 py-2.5">
                  <span className="inline-flex min-w-0 items-center gap-2.5">
                    <FileText aria-hidden className="size-[18px] shrink-0 text-muted-foreground" />
                    <code className="truncate font-mono text-sm">{file}</code>
                  </span>
                  <Button
                    size="sm"
                    onClick={() => {
                      setFile(null);
                      setReceipt(null);
                    }}
                  >
                    Check another
                  </Button>
                </div>
                {receipt === "checking" || receipt == null ? (
                  <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle aria-hidden className="size-4 animate-spin" />
                    Checking against the contract…
                  </span>
                ) : (
                  <ReceiptResult result={receipt} />
                )}
              </>
            )}
          </section>
        </Card>
      </div>
    </>
  );
}

function StatusSteps({ status }: { status: AuditStatus }) {
  return (
    <ol aria-label={`Audit status: ${AUDIT_LABEL[status]}`} className="flex flex-wrap gap-1.5">
      {(["pending", "verified", "rejected"] as const).map((s) => (
        <Badge
          as="li"
          key={s}
          tone={s !== status ? "ghost" : s === "verified" ? "ok" : s === "rejected" ? "bad" : "warn"}
          aria-current={s === status ? "step" : undefined}
        >
          {s === status && s === "verified" && <Check aria-hidden className="size-3" />}
          {AUDIT_LABEL[s]}
        </Badge>
      ))}
    </ol>
  );
}

function PublicRecord({ lookup }: { lookup: Lookup }) {
  if (lookup.kind === "idle" || lookup.kind === "loading") {
    return (
      <span className="inline-flex items-center gap-2 text-muted-foreground">
        <LoaderCircle aria-hidden className="size-4 animate-spin" />
        Reading the contract on Sepolia…
      </span>
    );
  }
  if (lookup.kind === "error") {
    return (
      <Callout tone="bad" icon={<TriangleAlert aria-hidden />}>
        {lookup.message}
      </Callout>
    );
  }
  if (lookup.kind === "free") {
    return (
      <div className="flex flex-col gap-2">
        <Eyebrow>Public record</Eyebrow>
        <h2 className="text-2xl leading-tight font-semibold">Not retired</h2>
        <p className="text-muted-foreground">
          No retirement on the contract covers serial <code className="font-mono text-[13px]">{lookup.serial}</code>.
        </p>
      </div>
    );
  }

  const r = lookup.record;
  const where = projectOfBatch(r.batchId);
  return (
    <section aria-labelledby="rec-h" className="contents">
      <div className="flex flex-wrap items-start justify-between gap-x-5 gap-y-3">
        <div className="flex flex-col gap-1">
          <Eyebrow>Public record · read live from Sepolia</Eyebrow>
          <h2 id="rec-h" className="text-2xl leading-tight font-semibold">
            Retirement #{r.id}
          </h2>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className="text-[13px] text-muted-foreground">Audit status</span>
          <StatusSteps status={r.audit} />
        </div>
      </div>

      {lookup.serial && (
        <Callout key="serial" className="animate-rise-fast">
          Serial <code className="font-mono text-[13px]">{lookup.serial}</code> is inside this retirement’s range.
        </Callout>
      )}

      <KeyValue>
        <dt>Project</dt>
        <dd>
          {where ? (
            <TransitionLink href={`/projects/${where.project.id}`}>{where.project.name}</TransitionLink>
          ) : (
            <span className="text-muted-foreground">Batch not in this site’s data</span>
          )}
        </dd>
        <dt>Batch</dt>
        <dd className="flex flex-wrap items-center gap-2">
          <code className="font-mono text-[13px]">{where?.batch.key ?? r.batchId.slice(0, 10)}</code>
          <Badge tone="warn">Simulated serials</Badge>
        </dd>
        <dt>Serial range</dt>
        <dd className="font-mono text-[13px] break-all">{where ? rangeLabel(where.batch, r.start, r.end) : `${r.start} → ${r.end}`}</dd>
        <dt>Credits</dt>
        <dd className="tabular-nums">{formatInt(r.end - r.start + 1)}</dd>
        <dt>Commitment</dt>
        <dd>
          <HashChip value={r.buyerCommitment} label="commitment hash" />
        </dd>
        <dt>Report version</dt>
        <dd>
          {r.reportVersion > 0 && where ? (
            <>
              <TransitionLink href={`/projects/${where.project.id}`} className="font-mono text-[13px]">
                v{r.reportVersion}
              </TransitionLink>{" "}
              <span className="text-[13px] text-muted-foreground">· the project’s latest report when retired</span>
            </>
          ) : (
            <span className="text-[13px] text-muted-foreground">No report anchored at retirement time</span>
          )}
        </dd>
        <dt>Buyer</dt>
        <dd className="flex items-center gap-2">
          <Lock aria-hidden className="size-4 text-seal" />
          Sealed · no name on-chain
        </dd>
        <dt>Retired at</dt>
        <dd className="text-[14px]">{r.retiredAt.toISOString().replace("T", " ").slice(0, 16)} UTC</dd>
        {lookup.retireTx && (
          <>
            <dt>Retirement tx</dt>
            <dd>
              <EtherscanLink hash={lookup.retireTx} />
            </dd>
          </>
        )}
        {lookup.attestTx && (
          <>
            <dt>Attestation tx</dt>
            <dd>
              <EtherscanLink hash={lookup.attestTx} />
            </dd>
          </>
        )}
      </KeyValue>
      <p className="border-t border-border pt-4 text-[13px] text-muted-foreground">
        Audit status moves once, from Pending to Verified or Rejected. After that it can’t be changed.
      </p>
    </section>
  );
}

function CheckRow({ ok, title, detail, index }: { ok: boolean; title: string; detail?: string; index: number }) {
  return (
    <li style={staggerStyle(index)} className="animate-rise stagger flex items-start gap-3 border-t border-border py-3 first:border-t-0">
      <span className={cn("grid size-6 shrink-0 place-items-center rounded-full", ok ? "bg-ok-soft text-ok" : "bg-bad-soft text-bad")}>
        {ok ? <Check aria-hidden className="size-3.5" /> : <X aria-hidden className="size-3.5" />}
      </span>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="font-semibold">{title}</span>
        {detail && <span className="text-[13px] text-muted-foreground">{detail}</span>}
      </span>
      <Badge tone={ok ? "ok" : "bad"} className="ml-auto">
        {ok ? "Pass" : "Fail"}
      </Badge>
    </li>
  );
}

function ReceiptResult({ result }: { result: ReceiptCheck }) {
  if (result.error && result.lots.length === 0) {
    return (
      <Callout tone="bad" icon={<TriangleAlert aria-hidden />}>
        {result.error}
      </Callout>
    );
  }
  const keys = Object.keys(RECEIPT_CHECKS).filter((k) => k !== "same_buyer_in_all_lots");
  const rows = [
    ...keys.map((k) => ({ title: RECEIPT_CHECKS[k], ok: result.lots.every((l) => !l.error && l.checks[k] === true) })),
    ...Object.entries(result.bundleChecks).map(([k, ok]) => ({ title: RECEIPT_CHECKS[k] ?? k, ok })),
  ];
  const name = buyerName(result.lei);
  const ids = result.lots.map((l) => `#${l.retirementId}`).join(", ");
  const errors = result.lots.filter((l) => l.error);

  return (
    <>
      <p className="text-[13px] text-muted-foreground">
        {result.lots.length} lot{result.lots.length === 1 ? "" : "s"} ({ids}) · {formatInt(result.quantity)} credits · buyer
        in this receipt: {name ? `${name} (fictional) · ` : ""}
        <code className="font-mono">{result.lei}</code>
      </p>
      <ol aria-label="Receipt checks">
        {rows.map((c, i) => (
          <CheckRow key={c.title} ok={c.ok} title={c.title} index={i} />
        ))}
      </ol>
      {errors.map((l) => (
        <p key={l.retirementId} className="text-[13px] text-bad">
          Lot #{l.retirementId}: {l.error}
        </p>
      ))}
      <div
        role="status"
        className={cn("animate-rise stagger flex items-center gap-3 rounded-[10px] px-4 py-3.5", result.valid ? "bg-ok-soft" : "bg-bad-soft")}
        style={staggerStyle(rows.length)}
      >
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-full text-card", result.valid ? "bg-ok" : "bg-bad")}>
          {result.valid ? <Check aria-hidden className="size-5" /> : <X aria-hidden className="size-5" />}
        </span>
        <span className="flex flex-col gap-0.5">
          <strong className={cn("text-lg", result.valid ? "text-ok" : "text-bad")}>
            {result.valid ? "Claim verified" : "Claim not verified"}
          </strong>
          <span>
            {result.valid
              ? `This receipt proves retirement ${ids}: ${formatInt(result.quantity)} credits. Audit: ${result.audit ? AUDIT_LABEL[result.audit].toLowerCase() : "unknown"}.`
              : "At least one check failed, so this receipt does not prove the claim."}
          </span>
        </span>
      </div>
    </>
  );
}

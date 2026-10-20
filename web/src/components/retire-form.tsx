"use client";

import { Check, Download, LoaderCircle, Lock, TriangleAlert } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { EtherscanLink, HashChip } from "@/components/hash";
import { TransitionLink } from "@/components/transition-link";
import { LocalDemoNotice } from "@/components/local-demo-notice";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Callout, Card, KeyValue } from "@/components/ui/card";
import { Input, Label, NativeSelect } from "@/components/ui/input";
import { BUYERS, ICVCM_LABEL, PROJECTS, type Batch, rangeLabel, serialLabel } from "@/lib/data";
import { cn, formatInt } from "@/lib/utils";

/** Only projects with simulated issuance batches can be retired from. */
const RETIRABLE = PROJECTS.filter((p) => p.batches.length > 0);

type Range = { id: number; start: number; end: number };

type PublicRetirement = {
  retirement_id: number;
  batch_id: string;
  start: number;
  end: number;
  buyer_commitment: string;
  report_version: number;
  audit_status: string;
};

type Outcome =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "success"; retirements: PublicRetirement[]; txs: string[]; gas: number; receipt: unknown }
  | { kind: "overlap"; conflict: Range | undefined; conflictId: number }
  | { kind: "error"; message: string };

const pad = (n: number) => String(n).padStart(9, "0");

/** Lots of a batch: [first + k*lot, first + (k+1)*lot - 1], the last one possibly shorter. */
function lotBounds(b: Batch, k: number): [number, number] {
  const s = b.first_serial + k * b.lot_size;
  return [s, Math.min(s + b.lot_size - 1, b.last_serial)];
}

function nextFreeLot(b: Batch, retired: Range[]) {
  const taken = new Set(retired.map((r) => Math.floor((r.start - b.first_serial) / b.lot_size)));
  const lots = Math.ceil(b.quantity / b.lot_size);
  for (let k = 0; k < lots; k++) if (!taken.has(k)) return k;
  return -1;
}

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`/api/os/${path}`, { cache: "no-store", ...init });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

/** The retired ranges of a batch, from the API (which reads the contract). */
async function fetchRetired(batch: Batch): Promise<{ ranges: Range[]; error: string | null }> {
  const r = await api(`retirements?project_id=${encodeURIComponent(batch.key.split("|")[0])}`);
  if (!r.ok) return { ranges: [], error: r.body?.message ?? `API error ${r.status}` };
  const ranges = (r.body as PublicRetirement[])
    .filter((x) => x.batch_id.toLowerCase() === batch.batch_id.toLowerCase())
    .map((x) => ({ id: x.retirement_id, start: x.start, end: x.end }));
  return { ranges, error: null };
}

/** The first `lots` free lots after the last taken one, as [start, end] strings. */
function nextFreeRange(batch: Batch, ranges: Range[], lots = 2): [string, string] {
  const k = nextFreeLot(batch, ranges);
  if (k < 0) return ["", ""];
  const last = Math.min(k + lots - 1, Math.ceil(batch.quantity / batch.lot_size) - 1);
  return [String(lotBounds(batch, k)[0]), String(lotBounds(batch, last)[1])];
}

export function RetireForm() {
  const [projectId, setProjectId] = useState(RETIRABLE[0]?.id ?? "");
  const project = RETIRABLE.find((p) => p.id === projectId) ?? RETIRABLE[0];
  const [batchKey, setBatchKey] = useState(project.batches[0].key);
  const batch = project.batches.find((b) => b.key === batchKey) ?? project.batches[0];
  const [loaded, setLoaded] = useState<Record<string, { ranges: Range[]; error: string | null }>>({});
  const [edited, setEdited] = useState<{ key: string; start: string; end: string } | null>(null);
  const [buyerLei, setBuyerLei] = useState(BUYERS[0].lei);
  const [outcome, setOutcome] = useState<Outcome>({ kind: "idle" });
  const [downloaded, setDownloaded] = useState(false);
  const msgId = useId();

  const retired = loaded[batch.key]?.ranges ?? null;
  const apiError = loaded[batch.key]?.error ?? null;
  const [defaultStart, defaultEnd] = retired ? nextFreeRange(batch, retired) : ["", ""];
  const start = edited?.key === batch.key ? edited.start : defaultStart;
  const end = edited?.key === batch.key ? edited.end : defaultEnd;

  const reload = async (b: Batch) => {
    const result = await fetchRetired(b);
    setLoaded((x) => ({ ...x, [b.key]: result }));
    return result.ranges;
  };

  useEffect(() => {
    let live = true;
    fetchRetired(batch).then((result) => live && setLoaded((x) => ({ ...x, [batch.key]: result })));
    return () => {
      live = false;
    };
  }, [batch]);

  const setRange = (s: string, e: string) => setEdited({ key: batch.key, start: s, end: e });
  const fillNextFree = (ranges: Range[], lots = 2) => {
    const [s, e] = nextFreeRange(batch, ranges, lots);
    setRange(s, e);
  };
  const changeBatch = (key: string) => {
    setBatchKey(key);
    setEdited(null);
    setOutcome({ kind: "idle" });
  };

  const a = parseInt(start, 10);
  const b = parseInt(end, 10);
  const inBatch = Number.isFinite(a) && Number.isFinite(b) && a >= batch.first_serial && b >= a && b <= batch.last_serial;
  const aligned =
    inBatch &&
    (a - batch.first_serial) % batch.lot_size === 0 &&
    ((b - batch.first_serial + 1) % batch.lot_size === 0 || b === batch.last_serial);
  const valid = inBatch && aligned;
  const count = valid ? b - a + 1 : 0;
  const lots = valid ? Math.ceil(count / batch.lot_size) : 0;
  const hit = valid ? retired?.find((r) => a <= r.end && b >= r.start) : undefined;
  const buyer = BUYERS.find((x) => x.lei === buyerLei) ?? BUYERS[0];
  const busy = outcome.kind === "sending";
  const freeLot = retired ? nextFreeLot(batch, retired) : -1;

  const edit = (which: "start" | "end") => (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value.replace(/\D/g, "");
    setRange(which === "start" ? v : start, which === "end" ? v : end);
    setOutcome({ kind: "idle" });
    setDownloaded(false);
  };

  const rangeMessage = !inBatch
    ? `Enter a range inside the batch, ${pad(batch.first_serial)}–${pad(batch.last_serial)}, with “From” no higher than “To”.`
    : !aligned
      ? `Retirements are whole standard lots of ${formatInt(batch.lot_size)}: “From” must be 1 more than a multiple of ${formatInt(batch.lot_size)} and “To” a multiple (or the batch end).`
      : hit
        ? `Overlaps retirement #${hit.id} (${pad(hit.start)}–${pad(hit.end)}).`
        : freeLot >= 0
          ? `${lots} lot${lots === 1 ? "" : "s"}, one retirement each. Next free lot starts at ${pad(lotBounds(batch, freeLot)[0])}.`
          : "Every lot in this batch is retired.";

  const submit = async () => {
    if (!valid || busy) return;
    setOutcome({ kind: "sending" });
    setDownloaded(false);
    const r = await api("retirements", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ batch_key: batch.key, start: a, end: b, lei: buyer.lei }),
    });
    if (r.ok) {
      setOutcome({ kind: "success", retirements: r.body.retirements, txs: r.body.tx_hashes, gas: r.body.gas_used, receipt: r.body.receipt });
      void reload(batch);
    } else if (r.body?.error === "AlreadyRetired") {
      const id = Number(r.body.args?.conflictingRetirementId ?? r.body.args?.conflictingId ?? 0);
      const ranges = await reload(batch);
      setOutcome({ kind: "overlap", conflictId: id, conflict: ranges.find((x) => x.id === id) });
    } else {
      setOutcome({ kind: "error", message: r.body?.message ?? `Request failed (${r.status})` });
    }
  };

  const downloadReceipt = (receipt: unknown, ids: number[]) => {
    const blob = new Blob([JSON.stringify(receipt, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `receipt-${ids.join("-")}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setDownloaded(true);
  };

  return (
    <div className="flex flex-wrap items-start gap-6">
      <Card className="min-w-0 flex-[1_1_560px] p-7">
        <form
          className="flex flex-col gap-7"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          {apiError && (
            <LocalDemoNotice role="operator" detail={apiError} />
          )}

          <Step n={1} title="Project">
            <Label htmlFor="project">Project</Label>
            <NativeSelect
              id="project"
              value={project.id}
              disabled={busy}
              onChange={(e) => {
                const p = RETIRABLE.find((x) => x.id === e.target.value)!;
                setProjectId(p.id);
                changeBatch(p.batches[0].key);
              }}
            >
              {RETIRABLE.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} · {p.name}
                </option>
              ))}
            </NativeSelect>
            {project.report && (
              <p className="text-[13px] text-muted-foreground">
                Report v{project.anchors.at(-1)?.version} · overall {project.report.overall}/100 · ICVCM:{" "}
                {ICVCM_LABEL[project.report.methodology_status.status]} ·{" "}
                <TransitionLink href={`/projects/${project.id}`}>View report</TransitionLink>
              </p>
            )}
          </Step>

          <Step n={2} title="Issuance batch">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Label htmlFor="batch">Batch</Label>
              <Badge tone="warn">Simulated serials</Badge>
            </div>
            <NativeSelect id="batch" value={batch.key} disabled={busy} onChange={(e) => changeBatch(e.target.value)}>
              {project.batches.map((x) => (
                <option key={x.key} value={x.key}>
                  Vintage {x.vintage} · batch {String(x.batch_no).padStart(3, "0")} · {formatInt(x.quantity)} credits
                </option>
              ))}
            </NativeSelect>
            <p className="text-[13px] text-muted-foreground">
              Real vintage and issued quantity from CarbonPlan OffsetsDB; the serials are generated for this prototype
              in the form <code className="font-mono text-[13px]">{serialLabel(batch, 1)}</code> and exist in no
              registry.
            </p>
          </Step>

          <Step n={3} title="Serial range">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(160px,100%),1fr))] items-end gap-3">
              <div className="flex flex-col gap-2">
                <Label htmlFor="from">From serial</Label>
                <Input id="from" inputMode="numeric" autoComplete="off" className="font-mono" value={start} disabled={busy}
                  onChange={edit("start")} aria-invalid={!valid || !!hit} aria-describedby={msgId} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="to">To serial</Label>
                <Input id="to" inputMode="numeric" autoComplete="off" className="font-mono" value={end} disabled={busy}
                  onChange={edit("end")} aria-invalid={!valid || !!hit} aria-describedby={msgId} />
              </div>
              <div className="flex flex-col gap-2 pb-2.5">
                <span className="text-[13px] text-muted-foreground">Credits</span>
                <span className="text-xl font-semibold tabular-nums">{formatInt(count)}</span>
              </div>
            </div>
            <p id={msgId} className={cn("text-[13px]", !valid || hit ? "text-bad" : "text-muted-foreground")}>
              {rangeMessage}
            </p>
            <BatchBar batch={batch} retired={retired ?? []} a={a} b={b} valid={valid} overlapping={!!hit} />
          </Step>

          <Step n={4} title="Buyer company">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Label htmlFor="buyer">Buyer (legal entity)</Label>
              <Badge>Fictional companies</Badge>
            </div>
            <NativeSelect id="buyer" value={buyerLei} disabled={busy} onChange={(e) => setBuyerLei(e.target.value)}>
              {BUYERS.map((x) => (
                <option key={x.lei} value={x.lei}>
                  {x.name}
                </option>
              ))}
            </NativeSelect>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <span className="text-[13px] text-muted-foreground">LEI (valid check digits, not registered)</span>
              <code className="font-mono text-sm">{buyer.lei}</code>
            </div>
            <Callout tone="seal" icon={<Lock aria-hidden />}>
              The operator service encrypts the LEI to the auditor’s public key, with a fresh secret salt per lot.
              On-chain: serial range, commitment hash, vault hash, report version. <strong>Not on-chain:</strong> buyer
              name, LEI.
            </Callout>
          </Step>

          <div className="flex flex-wrap items-center gap-3 border-t border-border pt-5">
            <Button type="submit" variant="primary" disabled={!valid || busy || !!apiError}>
              {busy ? <LoaderCircle aria-hidden className="animate-spin" /> : null}
              {busy ? "Recording on Sepolia…" : `Retire ${formatInt(count)} credits`}
            </Button>
            <Button disabled={busy} onClick={() => retired && fillNextFree(retired)}>
              Next free lots
            </Button>
            <p className="flex-[1_1_200px] text-[13px] text-muted-foreground">
              Every lot is checked against the contract before the first transaction is sent.
            </p>
          </div>
        </form>
      </Card>

      <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-4">
        {outcome.kind === "sending" && (
          <Card key="sending" aria-live="polite" className="animate-rise-fast flex flex-col gap-2.5 p-7">
            <h2 className="inline-flex items-center gap-2 text-base font-semibold">
              <LoaderCircle aria-hidden className="size-4 animate-spin" />
              Recording {lots} lot{lots === 1 ? "" : "s"} on Sepolia
            </h2>
            <p className="text-muted-foreground">
              One transaction per lot; each waits for a block (about 12 seconds).
            </p>
          </Card>
        )}

        {outcome.kind === "success" && (
          <Card key="success" aria-live="polite" className="animate-rise-fast flex flex-col gap-5 p-7">
            <div className="flex items-start gap-3.5">
              <span className="grid size-10 shrink-0 place-items-center rounded-full bg-ok-soft text-ok">
                <Check aria-hidden className="size-5" />
              </span>
              <div className="flex flex-col gap-1.5">
                <h2 className="text-xl leading-snug font-semibold">
                  {outcome.retirements.length === 1
                    ? `Retirement #${outcome.retirements[0].retirement_id} recorded`
                    : `Retirements #${outcome.retirements[0].retirement_id}–#${outcome.retirements.at(-1)!.retirement_id} recorded`}
                </h2>
                <Badge tone="warn" dot className="self-start">
                  Audit: Pending
                </Badge>
              </div>
            </div>
            <KeyValue className="grid-cols-[minmax(0,110px)_minmax(0,1fr)]">
              {outcome.retirements.map((r, i) => (
                <LotRow key={r.retirement_id} batch={batch} r={r} tx={outcome.txs[i]} />
              ))}
              <dt>Gas used</dt>
              <dd className="tabular-nums">{formatInt(outcome.gas)}</dd>
            </KeyValue>
            <Callout tone="seal" icon={<Lock aria-hidden />}>
              <strong>No name on-chain.</strong> The public record holds only the ranges and commitments.{" "}
              {buyer.name} is readable by the auditor alone.
            </Callout>
            <div className="flex flex-col gap-3 border-t border-border pt-4">
              <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2.5">
                <Button variant="primary" onClick={() => downloadReceipt(outcome.receipt, outcome.retirements.map((r) => r.retirement_id))}>
                  <Download aria-hidden />
                  {downloaded ? "Receipt downloaded" : "Download receipt"}
                </Button>
                <TransitionLink href={`/verify?q=${outcome.retirements[0].retirement_id}`} className={buttonVariants()}>
                  Verify it
                </TransitionLink>
              </div>
              <Callout tone="warn" role="note" icon={<TriangleAlert aria-hidden />}>
                <strong>Keep this receipt private.</strong> It holds the buyer’s LEI and the secret salts that open the
                commitments. Anyone holding it can prove this claim. The server does not keep a plain-text copy, so this
                is the only chance to download it.
              </Callout>
            </div>
          </Card>
        )}

        {outcome.kind === "overlap" && (
          <Card key="overlap" role="alert" className="animate-rise-fast flex flex-col gap-[18px] border-bad p-7">
            <div className="flex items-start gap-3.5">
              <span className="grid size-10 shrink-0 place-items-center rounded-full bg-bad-soft text-bad">
                <TriangleAlert aria-hidden className="size-5" />
              </span>
              <div className="flex flex-col gap-1.5">
                <h2 className="text-xl leading-snug font-semibold">Already retired by retirement #{outcome.conflictId}</h2>
                <p className="text-muted-foreground">
                  The pre-flight check against the contract failed. No transaction was sent and nothing was recorded.
                </p>
              </div>
            </div>
            <KeyValue className="grid-cols-[minmax(0,130px)_minmax(0,1fr)]">
              <dt>Your range</dt>
              <dd className="font-mono text-[13px] break-all">{rangeLabel(batch, a, b)}</dd>
              {outcome.conflict && (
                <>
                  <dt>Retirement #{outcome.conflictId}</dt>
                  <dd className="font-mono text-[13px] break-all">{rangeLabel(batch, outcome.conflict.start, outcome.conflict.end)}</dd>
                </>
              )}
            </KeyValue>
            <div className="flex flex-wrap gap-2.5">
              <Button variant="primary" onClick={() => retired && (fillNextFree(retired, Math.max(lots, 1)), setOutcome({ kind: "idle" }))}>
                Use next free lots
              </Button>
              <TransitionLink href={`/verify?q=${outcome.conflictId}`} className={buttonVariants()}>
                View retirement #{outcome.conflictId}
              </TransitionLink>
            </div>
          </Card>
        )}

        {outcome.kind === "error" && (
          <Card key="error" role="alert" className="animate-rise-fast flex flex-col gap-2.5 border-bad p-7">
            <h2 className="text-base font-semibold text-bad">Not recorded</h2>
            <p className="text-muted-foreground">{outcome.message}</p>
          </Card>
        )}

        {outcome.kind === "idle" && (
          <Card key="idle" aria-live="polite" className="animate-rise-fast flex flex-col gap-2.5 border-dashed p-7">
            <h2 className="text-base font-semibold">Result</h2>
            <p className="text-muted-foreground">
              Nothing submitted yet. After retiring you’ll get one retirement number and commitment per lot, and a
              private receipt for the buyer.
            </p>
            {retired && retired.length > 0 && (
              <p className="text-[13px] text-muted-foreground">
                Try {pad(retired[0].start)}–{pad(retired[0].end)} to see the “already retired” error.
              </p>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

function LotRow({ batch, r, tx }: { batch: Batch; r: PublicRetirement; tx: string }) {
  return (
    <>
      <dt>#{r.retirement_id}</dt>
      <dd className="flex flex-col items-start gap-1.5">
        <span className="font-mono text-[13px] break-all">{rangeLabel(batch, r.start, r.end)}</span>
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <HashChip value={r.buyer_commitment} label={`commitment of retirement ${r.retirement_id}`} />
          <EtherscanLink hash={tx} />
        </span>
      </dd>
    </>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <legend className="mb-2 flex items-center gap-2.5 p-0">
        <span className="grid size-6 shrink-0 place-items-center rounded-full bg-secondary text-xs font-semibold">{n}</span>
        <span className="text-sm font-semibold">{title}</span>
      </legend>
      {children}
    </fieldset>
  );
}

function BatchBar({ batch, retired, a, b, valid, overlapping }: {
  batch: Batch; retired: Range[]; a: number; b: number; valid: boolean; overlapping: boolean;
}) {
  const pct = (x: number) => (x / batch.quantity) * 100;
  const retiredTotal = retired.reduce((n, r) => n + r.end - r.start + 1, 0);
  return (
    <div className="mt-1 flex flex-col gap-2">
      <div
        role="img"
        aria-label={`Batch ${batch.key}: ${formatInt(retiredTotal)} of ${formatInt(batch.quantity)} credits retired`}
        className="relative h-7 overflow-hidden rounded-md border border-border bg-secondary"
      >
        {retired.map((r) => (
          <div key={r.id} className="absolute inset-y-0 min-w-[3px] bg-input"
            style={{ left: `${pct(r.start - batch.first_serial)}%`, width: `${pct(r.end - r.start + 1)}%` }} />
        ))}
        {valid && (
          <div
            className={cn(
              "absolute inset-y-0.5 min-w-1 rounded-[3px] border-2 transition-[left,width,background-color,border-color] duration-500 ease-out",
              overlapping ? "border-bad bg-bad-soft" : "border-primary bg-primary-soft",
            )}
            style={{ left: `${pct(a - batch.first_serial)}%`, width: `${pct(b - a + 1)}%` }}
          />
        )}
      </div>
      <div className="flex flex-wrap justify-between gap-x-4 gap-y-1.5 text-[13px] text-muted-foreground">
        <span className="font-mono">{pad(batch.first_serial)}</span>
        <span className="flex flex-wrap gap-x-4 gap-y-1.5">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-3 rounded-sm bg-input" />
            Retired ({retired.length} lot{retired.length === 1 ? "" : "s"}, {formatInt(retiredTotal)} credits)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className={cn("size-3 rounded-sm border-2", overlapping ? "border-bad" : "border-primary")} />
            Your range
          </span>
        </span>
        <span className="font-mono">{pad(batch.last_serial)}</span>
      </div>
    </div>
  );
}

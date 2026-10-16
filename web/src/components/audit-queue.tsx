"use client";

import { Check, LoaderCircle, Lock, LockOpen, TriangleAlert, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EtherscanLink, HashChip } from "@/components/hash";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout, Card, Eyebrow, KeyValue, Tag } from "@/components/ui/card";
import { retirementTxs } from "@/lib/chain";
import {
  AUDIT_CHECKS,
  AUDIT_LABEL,
  AUDIT_TONE,
  type AuditStatus,
  buyerName,
  projectOfBatch,
  rangeLabel,
} from "@/lib/data";
import { cn, formatInt, staggerStyle } from "@/lib/utils";

type Item = {
  retirement_id: number;
  batch_id: string;
  project_id: string | null;
  start: number;
  end: number;
  quantity: number;
  buyer_commitment: string;
  audit_vault_hash: string;
  retired_at: string;
  audit_status: AuditStatus;
};

type Vault = { valid: boolean; checks: Record<string, boolean>; error: string | null; vault: { lei: string } | null };

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`/api/os/${path}`, { cache: "no-store", ...init });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.message ?? body?.detail ?? `API error ${res.status}`);
  return body;
}

const ago = (iso: string) => {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  return m < 60 ? `Recorded ${m} min ago` : m < 2880 ? `Recorded ${Math.round(m / 60)} h ago` : `Recorded ${Math.round(m / 1440)} days ago`;
};

export function AuditQueue() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [vaults, setVaults] = useState<Record<number, Vault | "opening">>({});
  const [txs, setTxs] = useState<Record<number, { retireTx?: string; attestTx?: string }>>({});
  const [deciding, setDeciding] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const list = ((await api("retirements")) as Item[]).sort((a, b) => b.retirement_id - a.retirement_id);
      setItems(list);
      setError(null);
      setSelectedId((id) => id ?? list.find((x) => x.audit_status === "pending")?.retirement_id ?? list[0]?.retirement_id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setItems([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selectedId == null || txs[selectedId]) return;
    retirementTxs(selectedId)
      .then((t) => setTxs((x) => ({ ...x, [selectedId]: t })))
      .catch(() => setTxs((x) => ({ ...x, [selectedId]: {} })));
  }, [selectedId, txs]);

  if (items == null) {
    return (
      <span className="inline-flex items-center gap-2 text-muted-foreground">
        <LoaderCircle aria-hidden className="size-4 animate-spin" />
        Loading retirements…
      </span>
    );
  }
  if (error) {
    return (
      <Callout tone="bad" icon={<TriangleAlert aria-hidden />}>
        <strong>Auditor API not reachable.</strong> {error}
      </Callout>
    );
  }

  const pending = items.filter((x) => x.audit_status === "pending");
  const finals = items.filter((x) => x.audit_status !== "pending");
  const current = items.find((x) => x.retirement_id === selectedId);
  if (!current) return <p className="text-muted-foreground">No retirements on the contract yet.</p>;

  const where = projectOfBatch(current.batch_id);
  const vault = vaults[current.retirement_id];
  const opened = vault && vault !== "opening" ? vault : null;
  const status = current.audit_status;
  const checkKeys = opened ? Object.keys(opened.checks) : [];
  const passed = checkKeys.filter((k) => opened!.checks[k]).length;
  const tx = txs[current.retirement_id] ?? {};

  const open = async () => {
    const id = current.retirement_id;
    setVaults((v) => ({ ...v, [id]: "opening" }));
    try {
      const opened = (await api(`audit/${id}/open`, { method: "POST" })) as Vault;
      setVaults((v) => ({ ...v, [id]: opened }));
    } catch (e) {
      setVaults((v) => ({ ...v, [id]: { valid: false, checks: {}, error: e instanceof Error ? e.message : String(e), vault: null } }));
    }
  };

  const decide = async (valid: boolean) => {
    if (status !== "pending" || !opened || deciding) return;
    setDeciding(true);
    setDecideError(null);
    try {
      const out = await api(`audit/${current.retirement_id}/attest`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ valid }),
      });
      setTxs((x) => ({ ...x, [current.retirement_id]: { ...x[current.retirement_id], attestTx: out.tx_hash } }));
      await load();
    } catch (e) {
      setDecideError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeciding(false);
    }
  };

  return (
    <div className="flex flex-wrap items-start gap-6">
      <aside aria-label="Retirements" className="flex max-w-[380px] min-w-0 flex-[1_1_300px] flex-col gap-5">
        <QueueSection title={`Pending · ${pending.length}`}>
          {pending.length === 0 ? (
            <p className="rounded-[10px] border border-dashed border-input px-4 py-3.5 text-[13px] text-muted-foreground">
              Nothing waiting. New retirements appear here.
            </p>
          ) : (
            pending.map((item, i) => (
              <QueueButton key={item.retirement_id} item={item} index={i} selected={item.retirement_id === selectedId}
                onSelect={() => setSelectedId(item.retirement_id)} />
            ))
          )}
        </QueueSection>
        <QueueSection title={`Final · ${finals.length}`}>
          {finals.map((item, i) => (
            <QueueButton key={item.retirement_id} item={item} index={i} selected={item.retirement_id === selectedId}
              onSelect={() => setSelectedId(item.retirement_id)} />
          ))}
        </QueueSection>
      </aside>

      <Card className="flex min-w-0 flex-[999_1_560px] flex-col gap-6 p-7">
        <section aria-labelledby="det-h" className="contents">
          <div className="flex flex-wrap items-start justify-between gap-x-5 gap-y-3">
            <div className="flex flex-col gap-1">
              <Eyebrow>{where?.project.name ?? current.project_id}</Eyebrow>
              <h2 id="det-h" className="text-[26px] leading-tight font-semibold">
                Retirement #{current.retirement_id}
              </h2>
            </div>
            <Badge tone={AUDIT_TONE[status]} dot className="min-h-7 text-[13px]">
              {AUDIT_LABEL[status]}
            </Badge>
          </div>

          <KeyValue className="grid-cols-[minmax(0,130px)_minmax(0,1fr)]">
            <dt>Serial range</dt>
            <dd className="font-mono text-[13px] break-all">
              {where ? rangeLabel(where.batch, current.start, current.end) : `${current.start} → ${current.end}`}
            </dd>
            <dt>Credits</dt>
            <dd className="tabular-nums">{formatInt(current.quantity)}</dd>
            <dt>Commitment</dt>
            <dd>
              <HashChip value={current.buyer_commitment} label="commitment hash" />
            </dd>
            <dt>Vault hash</dt>
            <dd>
              <HashChip value={current.audit_vault_hash} label="vault hash" />
            </dd>
            {tx.retireTx && (
              <>
                <dt>Retirement tx</dt>
                <dd>
                  <EtherscanLink hash={tx.retireTx} />
                </dd>
              </>
            )}
          </KeyValue>

          {vault === "opening" ? (
            <span className="inline-flex items-center gap-2 text-muted-foreground">
              <LoaderCircle aria-hidden className="size-4 animate-spin" />
              Opening the vault…
            </span>
          ) : opened ? (
            <>
              {opened.vault ? (
                <div key={`vault-${current.retirement_id}`} className="animate-rise-fast flex flex-col gap-3.5 rounded-xl border border-seal bg-seal-soft px-6 py-[22px]">
                  <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                    <Tag className="text-xs [&_svg]:size-4">
                      <LockOpen aria-hidden />
                      Vault open · decrypted with the auditor key
                    </Tag>
                    <Badge>Fictional company</Badge>
                  </div>
                  <p className="text-[22px] leading-snug font-semibold">{buyerName(opened.vault.lei) ?? "Unknown LEI"}</p>
                  <KeyValue className="grid-cols-[minmax(0,130px)_minmax(0,1fr)]">
                    <dt>LEI</dt>
                    <dd>
                      <code className="font-mono text-sm">{opened.vault.lei}</code>
                    </dd>
                    <dt>Name source</dt>
                    <dd className="text-[13px] text-muted-foreground">
                      The vault holds only the LEI; the name comes from the demo directory (in production, a GLEIF lookup).
                    </dd>
                  </KeyValue>
                </div>
              ) : (
                <Callout tone="bad" icon={<TriangleAlert aria-hidden />}>
                  {opened.error ?? "The vault could not be opened."}
                </Callout>
              )}

              {checkKeys.length > 0 && (
                <div key={`checks-${current.retirement_id}`} className="flex flex-col gap-1.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="text-[17px] font-semibold">Checks</h3>
                    <span className="text-[13px] text-muted-foreground tabular-nums">
                      {passed} of {checkKeys.length} checks passed
                    </span>
                  </div>
                  <ol aria-label="Audit checks">
                    {checkKeys.map((k, i) => {
                      const ok = opened.checks[k];
                      const [title, pass, fail] = AUDIT_CHECKS[k] ?? [k, "", ""];
                      return (
                        <li key={k} style={staggerStyle(i)} className="animate-rise stagger flex items-start gap-3 border-t border-border py-3 first:border-t-0">
                          <span className={cn("grid size-6 shrink-0 place-items-center rounded-full", ok ? "bg-ok-soft text-ok" : "bg-bad-soft text-bad")}>
                            {ok ? <Check aria-hidden className="size-3.5" /> : <X aria-hidden className="size-3.5" />}
                          </span>
                          <span className="flex min-w-0 flex-auto flex-col gap-0.5">
                            <span className="font-semibold">{title}</span>
                            <span className="text-[13px] text-muted-foreground">{ok ? pass : fail}</span>
                          </span>
                          <Badge tone={ok ? "ok" : "bad"}>{ok ? "Pass" : "Fail"}</Badge>
                        </li>
                      );
                    })}
                  </ol>
                </div>
              )}
            </>
          ) : (
            <div key={`sealed-${current.retirement_id}`} className="animate-rise-fast flex flex-wrap items-center gap-x-6 gap-y-4 rounded-xl bg-seal-soft p-6">
              <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-card text-seal">
                <Lock aria-hidden className="size-[22px]" />
              </span>
              <div className="flex flex-[1_1_260px] flex-col gap-1">
                <strong className="font-semibold">Buyer identity is sealed</strong>
                <span className="text-[13px]">
                  Opening decrypts the vault with the auditor’s private key. In this prototype that key sits on the demo
                  server; a real auditor would decrypt on their own machine.
                </span>
              </div>
              <Button variant="seal" onClick={() => void open()}>
                Open vault
              </Button>
            </div>
          )}

          {status === "pending" ? (
            <div key={`decide-${current.retirement_id}`} className="flex flex-col gap-3.5 border-t border-border pt-5">
              <div className="flex flex-wrap gap-3">
                <Button variant="primary" disabled={!opened || !opened.valid || deciding} onClick={() => void decide(true)}>
                  {deciding ? <LoaderCircle aria-hidden className="animate-spin" /> : <Check aria-hidden />}
                  Attest verified
                </Button>
                <Button variant="danger" disabled={!opened || deciding} onClick={() => void decide(false)}>
                  Reject
                </Button>
              </div>
              <p className="text-[13px] text-muted-foreground">
                {!opened
                  ? "Open the vault to review the checks before deciding."
                  : !opened.valid
                    ? "A check failed, so this retirement can only be rejected."
                    : "One decision per retirement. It is signed with the auditor key, written on-chain, and final: it can’t be changed or withdrawn."}
              </p>
              {decideError && <p className="text-[13px] text-bad">{decideError}</p>}
            </div>
          ) : (
            <Callout key={`final-${current.retirement_id}-${status}`} tone={status === "verified" ? "ok" : "bad"} icon={<Lock aria-hidden />} className="animate-rise-fast">
              <p>
                <strong>Final: {AUDIT_LABEL[status]}.</strong> This status is recorded on-chain and cannot be changed.
              </p>
              {tx.attestTx && (
                <EtherscanLink hash={tx.attestTx} className="min-h-8">
                  Attestation on Sepolia Etherscan
                </EtherscanLink>
              )}
            </Callout>
          )}
        </section>
      </Card>
    </div>
  );
}

function QueueSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="px-1 text-xs leading-4 font-semibold tracking-[0.08em] text-muted-foreground uppercase">{title}</h2>
      <ul className="flex flex-col gap-1">{children}</ul>
    </section>
  );
}

function QueueButton({ item, index, selected, onSelect }: { item: Item; index: number; selected: boolean; onSelect: () => void }) {
  const where = projectOfBatch(item.batch_id);
  return (
    <li style={staggerStyle(index)} className="animate-rise stagger">
      <button
        type="button"
        aria-pressed={selected}
        onClick={onSelect}
        className={cn(
          "flex min-h-11 w-full cursor-pointer flex-col items-stretch gap-1 rounded-[10px] border border-transparent px-4 py-3.5 text-left text-foreground transition-[background-color,border-color,box-shadow] duration-300 hover:bg-secondary",
          selected && "border-input bg-card shadow-sm hover:bg-card",
        )}
      >
        <span className="flex items-center justify-between gap-2">
          <strong className="font-semibold">Retirement #{item.retirement_id}</strong>
          <Badge tone={AUDIT_TONE[item.audit_status]} dot>
            {AUDIT_LABEL[item.audit_status]}
          </Badge>
        </span>
        <span className="text-[13px] text-muted-foreground">
          {where?.project.id ?? item.project_id} · <span className="tabular-nums">{formatInt(item.quantity)}</span> credits
        </span>
        {item.audit_status === "pending" && <span className="text-[13px] text-muted-foreground">{ago(item.retired_at)}</span>}
      </button>
    </li>
  );
}

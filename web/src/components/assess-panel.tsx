"use client";

import { Check, FileUp, LoaderCircle, Minus, Play, TriangleAlert, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { EtherscanLink, HashChip } from "@/components/hash";
import { TransitionLink } from "@/components/transition-link";
import { LocalDemoNotice } from "@/components/local-demo-notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout, Card, KeyValue } from "@/components/ui/card";
import { Input, Label, NativeSelect } from "@/components/ui/input";
import { CHECK_NAME, DOCUMENT_ROLE_ONE, PRINCIPLE_NAME } from "@/lib/data";

type Doc = { role: string; covers: string[]; file_name: string; period: string | null; status: string };
type Summary = {
  overall: number | null;
  generated_at: string;
  method_hash: string;
  principles: { principle: string; status: string; score: number | null; review_flags: string[] }[];
  documents: number;
};
type Job = { status: "running" | "done" | "failed"; done: string[]; total: number; error: string | null };
type ProjectRow = {
  project_id: string;
  name: string;
  documents: Doc[];
  missing_roles: string[];
  published: Summary | null;
  draft: boolean;
  job: Job | null;
};
type Changed = { principle: string; id: string; question: string; before: string | null; after: string };
type Draft = {
  cost: number;
  report_hash: string;
  published: Summary | null;
  draft: Summary;
  changed_checks: Changed[];
  unchanged_checks: number;
  same_method: boolean;
};
type Published = {
  version: number;
  tx_hash: string;
  report_hash: string;
  chain_id: number;
  files_written: boolean;
  web_data_refreshed: boolean;
};

const ROLES = ["monitoring_report", "verification_report", "validation_report", "supporting"];

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`/api/os/${path}`, { cache: "no-store", ...init });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.message ?? body?.detail ?? `API error ${res.status}`);
  return body;
}

const flags = (s: Summary) => s.principles.reduce((n, p) => n + p.review_flags.length, 0);

/** The assessor's screen: add a document, run the assessment, compare the draft, publish and anchor it. */
export function AssessPanel() {
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pid, setPid] = useState<string>("");
  const [draft, setDraft] = useState<{ job: Job | null; draft: Draft | null } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [published, setPublished] = useState<Published | null>(null);
  const [useCache, setUseCache] = useState(true);

  const loadProjects = useCallback(async () => {
    try {
      const list: ProjectRow[] = await api("assess/projects");
      setRows(list);
      setPid((p) => p || list[0]?.project_id || "");
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const loadDraft = useCallback(async (id: string) => {
    if (!id) return;
    try {
      setDraft(await api(`assess/${id}/draft`));
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    let live = true;
    api("assess/projects")
      .then((list: ProjectRow[]) => {
        if (!live) return;
        setRows(list);
        setPid((p) => p || list[0]?.project_id || "");
      })
      .catch((e: unknown) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!pid) return;
    let live = true;
    api(`assess/${pid}/draft`)
      .then((x) => live && setDraft(x))
      .catch((e: unknown) => live && setActionError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, [pid]);

  const choose = (id: string) => {
    setPid(id);
    setDraft(null);
    setPublished(null);
    setActionError(null);
  };

  // poll while the assessment runs
  useEffect(() => {
    if (draft?.job?.status !== "running") return;
    const t = setInterval(() => void loadDraft(pid), 2000);
    return () => clearInterval(t);
  }, [draft?.job?.status, pid, loadDraft]);

  const act = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    setActionError(null);
    try {
      await fn();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  if (error) {
    return (
      <LocalDemoNotice role="assessor" detail={error} />
    );
  }
  if (!rows) {
    return (
      <p className="inline-flex items-center gap-2 text-muted-foreground">
        <LoaderCircle aria-hidden className="size-4 animate-spin" /> Loading projects…
      </p>
    );
  }

  const row = rows.find((r) => r.project_id === pid);
  const job = draft?.job;
  const d = draft?.draft;
  const running = job?.status === "running";

  return (
    <div className="flex flex-col gap-5">
      <Card className="flex flex-wrap items-end gap-x-6 gap-y-4 px-6 py-5">
        <div className="flex min-w-72 flex-1 flex-col gap-2">
          <Label htmlFor="project" className="font-semibold text-foreground">
            Project
          </Label>
          <NativeSelect id="project" value={pid} disabled={running} onChange={(e) => choose(e.target.value)}>
            {rows.map((r) => (
              <option key={r.project_id} value={r.project_id}>
                {r.project_id} · {r.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        {row?.published && (
          <p className="text-[13px] text-muted-foreground">
            Published: overall <strong className="text-foreground">{row.published.overall}</strong>/100 ·{" "}
            {row.published.generated_at.slice(0, 10)} ·{" "}
            <TransitionLink href={`/projects/${pid}`}>open report</TransitionLink>
          </p>
        )}
      </Card>

      {row && <Documents row={row} disabled={running || !!busy} onAdded={loadProjects} />}

      <Card className="flex flex-col gap-4 px-6 py-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Run the assessment</h2>
          <label className="inline-flex items-center gap-2 text-[13px] text-muted-foreground">
            <input type="checkbox" checked={useCache} onChange={(e) => setUseCache(e.target.checked)} disabled={running} />
            Reuse cached answers for unchanged excerpts (free and repeatable)
          </label>
        </div>
        <p className="text-[13px] text-muted-foreground">
          The same code as the published reports: 18 checks over an excerpt per principle (30,000 characters of the project description plus up to 15,000 from the other documents), each “found”
          citing a paragraph, a second model for review flags, instruction-like paragraphs screened out. About $0.02 a
          project when nothing is cached. The result is a draft until you publish it.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            disabled={running || !!busy || (row?.documents ?? []).some((x) => x.status !== "present")}
            onClick={() =>
              act("run", async () => {
                setPublished(null);
                await api(`assess/${pid}/run`, { method: "POST", body: JSON.stringify({ use_cache: useCache }) });
                await loadDraft(pid);
              })
            }
          >
            <Play aria-hidden className="size-4" /> Run assessment
          </Button>
          {(row?.documents ?? []).some((x) => x.status !== "present") && (
            <span className="text-[13px] text-bad">Some documents are not on this machine (see the list above).</span>
          )}
        </div>
        {job && (
          <ol className="flex flex-wrap gap-2" aria-label="Progress">
            {["additionality", "permanence", "robust_quantification", "no_double_counting", "safeguards"].map((k) => {
              const done = job.done.includes(k);
              return (
                <Badge as="li" key={k} tone={done ? "ok" : running ? "neutral" : "ghost"} className="gap-1.5">
                  {done ? <Check aria-hidden className="size-3" /> : running ? <LoaderCircle aria-hidden className="size-3 animate-spin" /> : <Minus aria-hidden className="size-3" />}
                  {PRINCIPLE_NAME[k] ?? k}
                </Badge>
              );
            })}
          </ol>
        )}
        {job?.status === "failed" && (
          <Callout tone="bad" icon={<TriangleAlert aria-hidden />}>
            <strong>The assessment failed.</strong> {job.error} The published report is unchanged.
          </Callout>
        )}
      </Card>

      {d && !running && <DraftView pid={pid} d={d} busy={busy} act={act} onDone={(p) => { setPublished(p); void loadDraft(pid); void loadProjects(); }} />}

      {published && (
        <Callout tone="ok" icon={<Check aria-hidden />}>
          <strong>
            Published and anchored as version {published.version}
            {published.chain_id === 11155111 ? " on Sepolia" : ` on chain ${published.chain_id}`}.
          </strong>{" "}
          {published.chain_id === 11155111 && <EtherscanLink hash={published.tx_hash} />}{" "}
          {!published.files_written
            ? "This is a local chain, so the published report files (which mirror Sepolia) were left unchanged."
            : published.web_data_refreshed
              ? "The web data was refreshed: the project page shows it after a reload in development, or after the next build (npm run build) in production."
              : "Refreshing the web data failed; run python scripts/export_web_data.py."}
        </Callout>
      )}
      {actionError && (
        <Callout tone="bad" icon={<TriangleAlert aria-hidden />}>
          {actionError}
        </Callout>
      )}
    </div>
  );
}

function Documents({ row, disabled, onAdded }: { row: ProjectRow; disabled: boolean; onAdded: () => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState("monitoring_report");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [state, setState] = useState<{ kind: "idle" | "busy" | "error" | "done"; message?: string }>({ kind: "idle" });

  const upload = async () => {
    if (!file) return;
    setState({ kind: "busy" });
    const q = new URLSearchParams({ role, file_name: file.name });
    if (from && to) q.set("period", `${from}/${to}`);
    try {
      const res = await fetch(`/api/os/assess/${row.project_id}/documents?${q}`, { method: "POST", body: file });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body?.message ?? body?.detail ?? `API error ${res.status}`);
      setState({ kind: "done", message: `Added as ${body.record.local_path}. Run the assessment to read it.` });
      setFile(null);
      await onAdded();
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  };

  return (
    <Card className="flex flex-col gap-4 px-6 py-5">
      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold">Documents read</h2>
        <p className="text-[13px] text-muted-foreground">
          From samples/manifest.json. PDFs stay on this machine and are not redistributed; the manifest keeps their
          SHA-256.
        </p>
      </div>
      <ul className="flex flex-col gap-1.5">
        {row.documents.map((x) => (
          <li key={x.file_name} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[14px]">
            <Badge tone={x.status === "present" ? "ok" : "bad"} dot className="min-w-24 justify-center">
              {x.status === "present" ? "on disk" : x.status.replace("_", " ")}
            </Badge>
            <span className="font-medium">{DOCUMENT_ROLE_ONE[x.role] ?? x.role}</span>
            {x.covers.length > 0 && (
              <span className="text-[13px] text-muted-foreground">
                (also {x.covers.map((c) => (DOCUMENT_ROLE_ONE[c] ?? c).toLowerCase()).join(", ")})
              </span>
            )}
            <span className="min-w-0 truncate text-[13px] text-muted-foreground" title={x.file_name}>
              {x.file_name}
            </span>
            {x.period && <span className="font-mono text-[12px] text-muted-foreground">{x.period}</span>}
          </li>
        ))}
      </ul>
      {row.missing_roles.length > 0 && (
        <p className="text-[13px] text-warn">
          Not held: {row.missing_roles.map((r) => (DOCUMENT_ROLE_ONE[r] ?? r).toLowerCase()).join(", ")}.
        </p>
      )}
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3 border-t border-border pt-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="pdf" className="font-semibold text-foreground">
            Add a PDF from the registry
          </Label>
          <input
            id="pdf"
            type="file"
            accept="application/pdf"
            disabled={disabled || state.kind === "busy"}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-[13px]"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="role">Role</Label>
          <NativeSelect id="role" value={role} onChange={(e) => setRole(e.target.value)} disabled={disabled}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {DOCUMENT_ROLE_ONE[r]}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="from">Period (monitoring/verification)</Label>
          <span className="flex items-center gap-2">
            <Input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} disabled={disabled} />
            <span aria-hidden>–</span>
            <Input aria-label="Period end" type="date" value={to} onChange={(e) => setTo(e.target.value)} disabled={disabled} />
          </span>
        </div>
        <Button disabled={!file || disabled || state.kind === "busy"} onClick={() => void upload()}>
          {state.kind === "busy" ? <LoaderCircle aria-hidden className="size-4 animate-spin" /> : <Upload aria-hidden className="size-4" />}
          Add document
        </Button>
      </div>
      {state.kind === "done" && <p className="text-[13px] text-ok">{state.message}</p>}
      {state.kind === "error" && <p className="text-[13px] text-bad">{state.message}</p>}
    </Card>
  );
}

function DraftView({
  pid,
  d,
  busy,
  act,
  onDone,
}: {
  pid: string;
  d: Draft;
  busy: string | null;
  act: (label: string, fn: () => Promise<void>) => Promise<void>;
  onDone: (p: Published | null) => void;
}) {
  const before = d.published;
  return (
    <Card className="flex flex-col gap-4 px-6 py-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Draft</h2>
        <Badge tone="warn">Not published</Badge>
      </div>
      <KeyValue>
        <dt>Overall</dt>
        <dd className="tabular-nums">
          {before ? `${before.overall} → ` : ""}
          <strong>{d.draft.overall}</strong>/100
        </dd>
        <dt>Principles</dt>
        <dd className="flex flex-col gap-0.5 text-[14px]">
          {d.draft.principles.map((p) => {
            const old = before?.principles.find((x) => x.principle === p.principle);
            return (
              <span key={p.principle}>
                {PRINCIPLE_NAME[p.principle] ?? p.principle}:{" "}
                <span className="tabular-nums">
                  {old ? `${old.score ?? "n/a"} → ` : ""}
                  {p.score ?? "n/a"}
                </span>
              </span>
            );
          })}
        </dd>
        <dt>Checks</dt>
        <dd className="text-[14px]">
          {d.changed_checks.length} changed, {d.unchanged_checks} unchanged · {flags(d.draft)} marked for review
          {before ? ` (was ${flags(before)})` : ""}
        </dd>
        <dt>Documents</dt>
        <dd className="text-[14px]">
          {before ? `${before.documents} → ` : ""}
          {d.draft.documents} files read
        </dd>
        <dt>Method</dt>
        <dd className="text-[14px]">{d.same_method ? "unchanged" : "changed (models, questions, prompt or excerpt rule)"}</dd>
        <dt>Cost</dt>
        <dd className="tabular-nums">${d.cost.toFixed(4)}</dd>
        <dt>Report hash</dt>
        <dd>
          <HashChip value={d.report_hash} label="draft report hash" />
        </dd>
      </KeyValue>
      {d.changed_checks.length > 0 && (
        <ul className="flex flex-col gap-1.5 border-t border-border pt-3">
          {d.changed_checks.map((c) => (
            <li key={`${c.principle}-${c.id}`} className="flex flex-wrap items-center gap-x-3 text-[14px]">
              <span className="font-mono text-[12px] text-muted-foreground">{c.id}</span>
              <span title={c.question}>{CHECK_NAME[c.id] ?? c.question}</span>
              <span className="text-muted-foreground">
                {c.before === null ? "new" : c.before === "yes" ? "found" : "not found"} →{" "}
                <strong className={c.after === "yes" ? "text-ok" : "text-foreground"}>{c.after === "yes" ? "found" : "not found"}</strong>
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-3 border-t border-border pt-4">
        <Button
          variant="seal"
          disabled={!!busy}
          onClick={() =>
            act("publish", async () => {
              if (!window.confirm(`Replace reports/${pid}.json and anchor the new version on-chain? Earlier versions stay readable.`)) {
                return;
              }
              onDone(await api(`assess/${pid}/publish`, { method: "POST" }));
            })
          }
        >
          {busy === "publish" ? <LoaderCircle aria-hidden className="size-4 animate-spin" /> : <FileUp aria-hidden className="size-4" />}
          Publish and anchor
        </Button>
        <Button
          variant="danger"
          disabled={!!busy}
          onClick={() =>
            act("discard", async () => {
              await api(`assess/${pid}/discard`, { method: "POST" });
              onDone(null);
            })
          }
        >
          Discard draft
        </Button>
      </div>
    </Card>
  );
}

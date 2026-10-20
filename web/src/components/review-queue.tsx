"use client";

import { Check, LoaderCircle, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { LocalDemoNotice } from "@/components/local-demo-notice";
import { TransitionLink } from "@/components/transition-link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { CHECK_NAME, type Evidence, PRINCIPLE_NAME } from "@/lib/data";

type Decision = { decision: "found" | "not_found" | "unclear"; note: string; reviewed_at: string; model_answer: string | null };
type Item = {
  project_id: string;
  name: string;
  principle: string;
  check_id: string;
  question: string;
  answer: "yes" | "no" | null;
  evidence: Evidence[];
  second_opinion_p_yes: number | null;
  decision: Decision | null;
  in_published_report: boolean;
};
type Paragraph = { id: string; page: number; text: string };

const DECISION_LABEL = { found: "Found", not_found: "Not found", unclear: "Unclear" } as const;

async function api(path: string, init?: RequestInit) {
  const res = await fetch(`/api/os/${path}`, { cache: "no-store", ...init });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.message ?? body?.detail ?? `API error ${res.status}`);
  return body;
}

const key = (i: Item) => `${i.project_id}|${i.principle}|${i.check_id}`;

/** The checks the two models disagree on, for a person to decide with the excerpt the models read. */
export function ReviewQueue() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api("review/queue")
      .then((x: Item[]) => live && setItems(x))
      .catch((e: unknown) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, []);

  if (error) return <LocalDemoNotice role="assessor" detail={error} />;
  if (!items) {
    return (
      <p className="inline-flex items-center gap-2 text-muted-foreground">
        <LoaderCircle aria-hidden className="size-4 animate-spin" /> Loading the review queue…
      </p>
    );
  }
  const decided = items.filter((i) => i.decision).length;
  const onSaved = (i: Item, d: Decision) => setItems((xs) => xs!.map((x) => (key(x) === key(i) ? { ...x, decision: d } : x)));

  return (
    <div className="flex flex-col gap-5">
      <Card className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-6 py-4">
        <p>
          <strong className="tabular-nums">{decided}</strong> of <strong className="tabular-nums">{items.length}</strong> flagged
          checks decided.
        </p>
        <p className="max-w-[640px] text-[13px] text-muted-foreground">
          Decisions are saved in <code className="font-mono">reviews/&lt;project&gt;.json</code> and take effect when the
          report is assessed again and published on the <TransitionLink href="/assess">Assess</TransitionLink> screen
          (cached answers make that free). The models’ answers stay in the report next to yours.
        </p>
      </Card>
      {items.length === 0 && <p className="text-muted-foreground">No check is flagged for review.</p>}
      <ol className="flex flex-col gap-4">
        {items.map((i) => (
          <ReviewItem key={key(i)} item={i} onSaved={onSaved} />
        ))}
      </ol>
    </div>
  );
}

function ReviewItem({ item, onSaved }: { item: Item; onSaved: (i: Item, d: Decision) => void }) {
  const [choice, setChoice] = useState<Decision["decision"] | null>(item.decision?.decision ?? null);
  const [note, setNote] = useState(item.decision?.note ?? "");
  const [state, setState] = useState<"idle" | "saving" | "saved" | string>("idle");
  const [excerpt, setExcerpt] = useState<Paragraph[] | "loading" | null>(null);
  const [query, setQuery] = useState("");

  const shown = useMemo(() => {
    if (!Array.isArray(excerpt)) return [];
    const q = query.trim().toLowerCase();
    return q ? excerpt.filter((p) => p.text.toLowerCase().includes(q)) : excerpt;
  }, [excerpt, query]);

  const loadExcerpt = async () => {
    setExcerpt("loading");
    try {
      setExcerpt((await api(`review/${item.project_id}/${item.principle}/excerpt`)).paragraphs);
    } catch (e) {
      setExcerpt(null);
      setState(e instanceof Error ? e.message : String(e));
    }
  };

  const save = async () => {
    if (!choice) return;
    setState("saving");
    try {
      const res = await api(`review/${item.project_id}`, {
        method: "POST",
        body: JSON.stringify({ principle: item.principle, check_id: item.check_id, decision: choice, note }),
      });
      onSaved(item, res.decision);
      setState("saved");
    } catch (e) {
      setState(e instanceof Error ? e.message : String(e));
    }
  };

  const p = item.second_opinion_p_yes;
  return (
    <li className="flex flex-col gap-3 rounded-2xl border border-border/80 bg-card/85 p-5 backdrop-blur-md">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <Badge>{item.project_id}</Badge>
        <span className="text-[13px] text-muted-foreground">{PRINCIPLE_NAME[item.principle] ?? item.principle}</span>
        <span className="font-semibold">
          <span className="font-mono text-[12px] text-muted-foreground">{item.check_id}</span> {CHECK_NAME[item.check_id] ?? ""}
        </span>
        {item.decision ? (
          <Badge tone="ok" className="ml-auto gap-1">
            <Check aria-hidden className="size-3" /> Decided: {DECISION_LABEL[item.decision.decision]}
          </Badge>
        ) : (
          <Badge tone="warn" className="ml-auto">
            Needs a decision
          </Badge>
        )}
      </div>
      <p className="text-[14px] text-pretty">{item.question}</p>
      <p className="text-[13px] text-muted-foreground">
        Checklist model: <strong className="text-foreground">{item.answer === "yes" ? "found" : "not found"}</strong>
        {p != null && (
          <>
            {" "}
            · second model: <strong className="text-foreground">{p >= 0.5 ? "found" : "not found"}</strong> ({Math.round(100 * p)}%
            likely found)
          </>
        )}
      </p>
      {item.evidence.map((e) => (
        <blockquote key={e.paragraph_id} className="m-0 border-l-2 border-ok/60 pl-3 text-[14px]">
          “{e.text}” <span className="text-[12px] text-muted-foreground">(page {e.page} · {e.paragraph_id}, cited by the checklist model)</span>
        </blockquote>
      ))}

      {excerpt === null && (
        <Button size="sm" className="self-start" onClick={() => void loadExcerpt()}>
          Read the excerpt the models read
        </Button>
      )}
      {excerpt === "loading" && (
        <p className="inline-flex items-center gap-2 text-[13px] text-muted-foreground">
          <LoaderCircle aria-hidden className="size-4 animate-spin" /> Loading the excerpt…
        </p>
      )}
      {Array.isArray(excerpt) && (
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2">
            <Search aria-hidden className="size-4 text-muted-foreground" />
            <Input placeholder="Filter paragraphs (e.g. grievance, IRR, buffer)" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <p className="text-[12px] text-muted-foreground">
            {shown.length} of {excerpt.length} paragraphs
          </p>
          <ol className="flex max-h-96 flex-col gap-2 overflow-y-auto rounded-lg bg-secondary p-3">
            {shown.map((x) => (
              <li key={x.id} className="text-[13px] leading-relaxed">
                <span className="font-mono text-[11px] text-muted-foreground">
                  p.{x.page} · {x.id}
                </span>{" "}
                {x.text}
              </li>
            ))}
          </ol>
        </div>
      )}

      <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-border pt-3">
        <legend className="sr-only">Your decision</legend>
        {(Object.keys(DECISION_LABEL) as Decision["decision"][]).map((d) => (
          <label key={d} className="inline-flex items-center gap-1.5 text-[14px]">
            <input type="radio" name={`d-${item.project_id}-${item.principle}-${item.check_id}`} checked={choice === d} onChange={() => setChoice(d)} />
            {DECISION_LABEL[d]}
          </label>
        ))}
        <Input
          aria-label="Note (optional): the paragraph or reason"
          placeholder="Note (optional): the paragraph or reason"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="min-w-64 flex-1"
        />
        <Button variant="primary" size="sm" disabled={!choice || state === "saving"} onClick={() => void save()}>
          {state === "saving" ? <LoaderCircle aria-hidden className="size-4 animate-spin" /> : null}
          Save decision
        </Button>
      </fieldset>
      {state === "saved" && <p className="text-[13px] text-ok">Saved.</p>}
      {state !== "idle" && state !== "saving" && state !== "saved" && <p className="text-[13px] text-bad">{state}</p>}
    </li>
  );
}

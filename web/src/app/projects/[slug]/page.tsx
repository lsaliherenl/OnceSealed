import { Check, ExternalLink } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { AnchorCheck } from "@/components/anchor-check";
import { EtherscanLink, HashChip } from "@/components/hash";
import { DeterministicTag, IcvcmStamp, ScoreBar, SignalBanner } from "@/components/quality";
import { TransitionLink } from "@/components/transition-link";
import { Badge } from "@/components/ui/badge";
import { Card, KeyValue } from "@/components/ui/card";
import {
  PRINCIPLE_LABEL,
  PRINCIPLE_NAME,
  PRINCIPLE_ORDER,
  PRINCIPLE_TONE,
  PROJECTS,
  REPO_URL,
  getProject,
} from "@/lib/data";
import { staggerStyle } from "@/lib/utils";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return PROJECTS.map((p) => ({ slug: p.id }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const project = getProject((await params).slug);
  return { title: project ? project.name : "Project" };
}

const FLAG_TEXT: Record<string, string> = {
  decision_questions_disagree: "The decision model's two questions disagreed by two or more levels; worth a human look.",
};

/** Params are read inside Suspense so the route keeps an instant static shell (Cache Components). */
export default function ProjectReportPage({ params }: { params: Promise<Params> }) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-[1200px] px-6 pt-10 pb-[72px] text-muted-foreground md:px-8">Loading report…</main>
      }
    >
      <ProjectReport params={params} />
    </Suspense>
  );
}

async function ProjectReport({ params }: { params: Promise<Params> }) {
  const project = getProject((await params).slug);
  if (!project || !project.report) notFound();
  const report = project.report;
  const status = report.methodology_status;
  const latest = project.anchors.at(-1);
  const dropped = report.principles.reduce((n, p) => n + p.dropped_findings, 0);
  const quotes = report.principles.reduce((n, p) => n + p.quotes.length, 0);

  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-[13px] text-muted-foreground">
        <TransitionLink href="/projects" className="inline-flex min-h-11 items-center">
          Project quality
        </TransitionLink>
        <span aria-hidden>/</span>
        <span aria-current="page" className="text-foreground">
          {project.id}
        </span>
      </nav>

      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2.5">
          <h1 className="text-4xl leading-[1.15] font-semibold tracking-[-0.02em]">{project.name}</h1>
          <Badge>{project.id}</Badge>
        </div>
        <p className="text-muted-foreground">
          {project.country} · {project.category} · Source: {project.doc_type ?? "project document"},{" "}
          {report.document.pages} pages ·{" "}
          <a href={project.registry_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">
            Verra registry page <ExternalLink aria-hidden className="size-3.5" />
          </a>
        </p>
      </div>

      <SignalBanner>
        These findings summarize what the project document says and where. They are not a rating, a certification or
        an ICVCM assessment, and they can be wrong.
      </SignalBanner>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(440px,100%),1fr))] gap-5">
        <section aria-labelledby="icvcm-h" className="flex flex-col gap-4 rounded-xl bg-seal-soft p-6 transition-colors duration-300">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <h2 id="icvcm-h" className="text-base font-semibold">
              ICVCM methodology status
            </h2>
            <DeterministicTag className="rounded border border-border bg-card px-2.5 py-1.5" />
          </div>
          <IcvcmStamp status={status.status} size="lg" className="self-start" />
          <KeyValue>
            <dt>Methodology</dt>
            <dd className="font-mono text-[13px]">
              {status.code}
              {status.version ? ` v${status.version}` : ""}
            </dd>
            <dt>Decision</dt>
            <dd className="text-[14px]">{status.summary}</dd>
            <dt>Sources</dt>
            <dd className="flex flex-col gap-1">
              {status.sources.map((s) => (
                <a key={s} href={s} target="_blank" rel="noopener noreferrer" className="truncate text-[13px]" title={s}>
                  {s.replace(/^https?:\/\//, "")}
                </a>
              ))}
            </dd>
          </KeyValue>
          <p className="text-[13px] opacity-85">
            Looked up by methodology code in table version {status.table_version}. No model is involved, and this status
            is kept apart from the AI-assisted findings below.
          </p>
        </section>

        <Card className="flex flex-col gap-4 p-6">
          <h2 className="text-base font-semibold">Report provenance</h2>
          <KeyValue>
            <dt>Report hash</dt>
            <dd className="flex flex-col items-start gap-1.5">
              <HashChip value={report.hash} label="report hash" />
              <AnchorCheck projectId={project.id} reportHash={report.hash} />
            </dd>
            <dt>Method hash</dt>
            <dd className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <HashChip value={report.method_hash} label="method hash" />
              <span className="text-[13px] text-muted-foreground">models + prompt + questions + table</span>
            </dd>
            {latest && (
              <>
                <dt>Anchor transaction</dt>
                <dd className="flex flex-wrap items-center gap-x-3">
                  <EtherscanLink hash={latest.tx} />
                  <span className="text-[13px] text-muted-foreground">
                    version {latest.version}
                    {latest.version > 1 ? "; earlier versions stay readable" : ""}
                  </span>
                </dd>
              </>
            )}
            <dt>Models</dt>
            <dd className="text-[14px]">
              Quotes: <code className="font-mono text-[13px]">{report.method.llm_model}</code>
              <br />
              Evidence strength: <code className="font-mono text-[13px]">{report.method.decision_model}</code>
              <span className="block text-[13px] text-muted-foreground">Third-party models, not developed by this team.</span>
            </dd>
            <dt>Document</dt>
            <dd className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <HashChip value={report.document.sha256} label="document SHA-256" />
              <span className="truncate text-[13px] text-muted-foreground" title={report.document.file_name}>
                SHA-256 of the PDF (not redistributed)
              </span>
            </dd>
            <dt>Published file</dt>
            <dd>
              <a href={`${REPO_URL}/blob/main/reports/${project.id}.json`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[14px]">
                reports/{project.id}.json <ExternalLink aria-hidden className="size-3.5" />
              </a>
            </dd>
          </KeyValue>
        </Card>
      </div>

      <section aria-labelledby="ccp-h" className="flex flex-col gap-4 pt-3">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="flex flex-col gap-1.5">
            <h2 id="ccp-h" className="text-2xl leading-tight font-semibold tracking-[-0.01em]">
              Five Core Carbon Principles · overall {report.overall}/100
            </h2>
            <p className="text-muted-foreground">
              AI-assisted findings. All {quotes} quotes below were matched in the source PDF by code
              {dropped > 0 ? `; ${dropped} finding${dropped === 1 ? "" : "s"} whose quote could not be matched were dropped` : "; none had to be dropped"}.
            </p>
          </div>
          <Badge tone="warn">Signal, not verdict</Badge>
        </div>
        <ul aria-label="Status legend" className="flex flex-wrap gap-2">
          {PRINCIPLE_ORDER.slice(0, 5).map((s) => (
            <Badge as="li" key={s} tone={PRINCIPLE_TONE[s]} dot>
              {PRINCIPLE_LABEL[s]}
            </Badge>
          ))}
        </ul>

        <ol className="flex flex-col gap-3.5">
          {report.principles.map((p, i) => (
            <li
              key={p.principle}
              style={staggerStyle(i)}
              className="animate-rise stagger flex flex-wrap gap-x-10 gap-y-5 rounded-2xl border border-border/80 bg-card/85 p-6 backdrop-blur-md transition-colors duration-300"
            >
              <div className="flex max-w-[340px] flex-[1_1_260px] flex-col gap-3">
                <span className="font-mono text-[13px] text-muted-foreground">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="text-lg leading-snug font-semibold">{PRINCIPLE_NAME[p.principle] ?? p.principle}</h3>
                <Badge tone={PRINCIPLE_TONE[p.status]} dot className="self-start">
                  {PRINCIPLE_LABEL[p.status]}
                </Badge>
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-[13px] text-muted-foreground">Evidence score</span>
                    <span className="font-semibold tabular-nums">{p.score == null ? "n/a" : `${p.score} / 100`}</span>
                  </div>
                  <ScoreBar status={p.status} score={p.score} index={i} />
                </div>
                {p.review_flags.map((f) => (
                  <p key={f} className="text-[13px] text-warn">
                    {FLAG_TEXT[f] ?? f}
                  </p>
                ))}
              </div>
              <div className="flex min-w-0 flex-[999_1_480px] flex-col gap-3">
                <p className="text-pretty">{p.rationale}</p>
                {p.quotes.length > 0 ? (
                  <ul className="flex flex-col gap-2.5">
                    {p.quotes.map((q, j) => (
                      <li key={j}>
                        <blockquote className="m-0 flex flex-col gap-2 rounded-lg bg-secondary px-4 py-3.5 transition-colors duration-300">
                          <p className="leading-relaxed">“{q.text}”</p>
                          <footer className="flex flex-wrap items-center gap-x-3.5 gap-y-2 text-[13px] text-muted-foreground">
                            <span className="inline-flex items-center gap-1.5 font-semibold text-ok">
                              <Check aria-hidden className="size-3.5" />
                              {q.verification === "exact" ? "Verbatim match" : "Matched (letters and digits)"}
                            </span>
                            <span>Page {q.page}</span>
                          </footer>
                        </blockquote>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="rounded-lg border border-dashed border-input px-4 py-3.5 text-[13px] text-muted-foreground">
                    {p.status === "not_applicable"
                      ? "Not scored for this activity type (no reversal risk), so there is nothing to quote."
                      : "No verified passage in the document addresses this principle."}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <Card className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 px-6 py-5">
        <p className="flex-[1_1_420px] text-[13px] text-muted-foreground">{report.disclaimer}</p>
        {latest && <EtherscanLink hash={latest.tx}>Report v{latest.version} anchor on Sepolia Etherscan</EtherscanLink>}
      </Card>
    </main>
  );
}

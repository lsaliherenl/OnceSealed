import type { Metadata } from "next";
import { DeterministicTag, IcvcmStamp, SignalBanner } from "@/components/quality";
import { TransitionLink } from "@/components/transition-link";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, Eyebrow, Tag } from "@/components/ui/card";
import {
  ICVCM_LABEL,
  METHODOLOGY_TABLE_VERSION,
  PRINCIPLE_LABEL,
  PRINCIPLE_ORDER,
  PRINCIPLE_TONE,
  PROJECTS,
  type IcvcmStatus,
  principleCounts,
} from "@/lib/data";
import { staggerStyle } from "@/lib/utils";

export const metadata: Metadata = { title: "Project quality" };

const STATUSES = Object.keys(ICVCM_LABEL) as IcvcmStatus[];
const SCORES = PROJECTS.flatMap((p) => (p.report ? [p.report.overall] : []));

export default function ProjectsPage() {
  const shown = STATUSES.filter((s) => PROJECTS.some((p) => p.report?.methodology_status.status === s));
  return (
    <main className="reveal mx-auto flex max-w-[1200px] flex-col gap-7 px-6 md:px-8 pt-10 pb-[72px]">
      <div className="flex max-w-[760px] flex-col gap-2.5">
        <Eyebrow>Project quality</Eyebrow>
        <h1 className="text-4xl leading-[1.15] font-semibold tracking-[-0.02em]">
          What the project documents say, and where they say it
        </h1>
        <p className="text-[17px] text-pretty text-muted-foreground">
          AI-assisted reading of each project’s public Verra document against five ICVCM Core Carbon Principles. The
          methodology status is a separate, deterministic lookup.
        </p>
      </div>

      <SignalBanner>
        Findings summarize evidence located in the documents. They are not a rating, a certification or an ICVCM
        assessment, and they can be wrong. Their accuracy has not yet been measured against human labels.
      </SignalBanner>

      <Card className="flex flex-wrap items-center gap-x-10 gap-y-4 px-6 py-5">
        <div className="flex flex-[1_1_320px] flex-col gap-1">
          <h2 className="text-[15px] font-semibold">ICVCM methodology status</h2>
          <DeterministicTag>Deterministic lookup · not AI</DeterministicTag>
          <p className="text-[13px] text-muted-foreground">
            Read from a hand-compiled, sourced table of published ICVCM decisions (version {METHODOLOGY_TABLE_VERSION}).
            It describes the methodology, not the individual project.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          {shown.map((s) => (
            <IcvcmStamp key={s} status={s} />
          ))}
        </div>
      </Card>

      <section aria-labelledby="list-h" className="flex flex-col gap-3.5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
          <h2 id="list-h" className="text-xl font-semibold">
            {PROJECTS.length} Verra projects
          </h2>
          <p className="text-[13px] text-muted-foreground">Real public project documents · sorted by overall score</p>
        </div>
        <Card className="overflow-hidden">
          <ul>
            {PROJECTS.map((p, i) => {
              const counts = principleCounts(p);
              const latest = p.anchors.at(-1);
              return (
                <li
                  key={p.id}
                  style={staggerStyle(i)}
                  className="animate-rise stagger flex flex-wrap items-center gap-x-7 gap-y-4 px-6 py-[22px] transition-colors duration-300 border-t border-border first:border-t-0 hover:bg-secondary"
                >
                  <div className="flex min-w-0 flex-[1_1_280px] flex-col gap-1">
                    <TransitionLink href={`/projects/${p.id}`} className="text-[17px] font-semibold text-foreground no-underline">
                      {p.name}
                    </TransitionLink>
                    <p className="text-[13px] text-muted-foreground">
                      {p.id} · {p.country} · {p.category}
                    </p>
                  </div>
                  {p.report && (
                    <div className="flex flex-[0_1_230px] flex-col gap-1.5">
                      <DeterministicTag>
                        ICVCM · {p.report.methodology_status.code}
                        {p.report.methodology_status.version ? ` v${p.report.methodology_status.version}` : ""}
                      </DeterministicTag>
                      <IcvcmStamp status={p.report.methodology_status.status} className="self-start" />
                    </div>
                  )}
                  <div className="flex flex-[1_1_300px] flex-col gap-1.5">
                    <Tag className="text-muted-foreground">Principle findings · AI-assisted</Tag>
                    <ul className="flex flex-wrap gap-1.5">
                      {PRINCIPLE_ORDER.filter((s) => counts[s]).map((s) => (
                        <Badge as="li" key={s} tone={PRINCIPLE_TONE[s]}>
                          <span className="tabular-nums">{counts[s]}</span> {PRINCIPLE_LABEL[s].toLowerCase()}
                        </Badge>
                      ))}
                    </ul>
                  </div>
                  <div className="flex flex-[0_0_120px] flex-col gap-0.5">
                    <span className="text-[13px] text-muted-foreground">Overall · report</span>
                    <span className="font-mono text-[13px]">
                      <span className="font-semibold">{p.report?.overall ?? "–"}</span>/100 · v{latest?.version ?? "–"}
                    </span>
                  </div>
                  <TransitionLink href={`/projects/${p.id}`} aria-label={`Open report for ${p.name}`} className={buttonVariants()}>
                    Open report →
                  </TransitionLink>
                </li>
              );
            })}
          </ul>
        </Card>
        <p className="text-[13px] text-muted-foreground">
          Overall scores range from {Math.min(...SCORES)} to {Math.max(...SCORES)}; the per-principle findings carry more
          information than the total.
          A document can evidence a principle well while ICVCM still rejects its methodology, which is why the two are
          shown apart.
        </p>
      </section>
    </main>
  );
}

import { CircleCheck, FileText, Lock } from "lucide-react";
import { EtherscanLink, HashChip } from "@/components/hash";
import { TransitionLink } from "@/components/transition-link";
import { Badge, type Tone } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Eyebrow } from "@/components/ui/card";
import { ANONYMITY, NETWORK, PROJECTS, REPO_URL } from "@/lib/data";
import { cn, staggerStyle } from "@/lib/utils";

const PILLARS = [
  {
    n: "01",
    title: "Once",
    lead: "Each credit is retired once.",
    body: "Retirements are recorded as serial ranges in standard lots. The contract refuses any range that overlaps an earlier retirement, and anyone can check a serial.",
    icon: CircleCheck,
    tile: "bg-primary-soft text-primary",
    links: [
      { href: "/retire", label: "Retire credits" },
      { href: "/verify", label: "Check a serial" },
    ],
  },
  {
    n: "02",
    title: "Sealed",
    lead: "Buyer identity is encrypted; the auditor can verify it.",
    body: "Only a commitment hash goes on-chain. The buyer’s LEI is encrypted to the auditor, who checks it and attests the result on-chain once. Not zero-knowledge: a hash commitment plus encryption.",
    icon: Lock,
    tile: "bg-seal-soft text-seal",
    links: [{ href: "/auditor", label: "Open the auditor view" }],
  },
  {
    n: "03",
    title: "Evidence-backed",
    lead: "Every AI finding cites the source PDF.",
    body: "Each “found” check points to a paragraph of the project’s public Verra documents, shown with its page. A “found” without a cited paragraph is not counted, and a second model’s disagreement is marked for review.",
    icon: FileText,
    tile: "bg-primary-soft text-primary",
    links: [{ href: "/projects", label: "See project quality" }],
  },
];

const SCREENS: { href: string; role: string; tone?: Tone; title: string; body: string }[] = [
  { href: "/projects", role: "Public", title: "Project quality", body: `Methodology status and five principle findings for ${PROJECTS.length} real Verra projects.` },
  { href: "/retire", role: "Registry operator", title: "Retire credits", body: "Retire whole lots of simulated serials for a fictional buyer and issue a private receipt." },
  { href: "/verify", role: "Anyone", title: "Verify a retirement", body: "Look up a retirement or serial and check a receipt against the chain." },
  { href: "/auditor", role: "Auditor", tone: "seal", title: "Audit queue", body: "Open the sealed identity, review the checks and attest once." },
  { href: "/assess", role: "Assessor", tone: "seal", title: "Assess a project", body: "Add a registry document, run the checks, compare the draft and anchor a new report version." },
];

export default function OverviewPage() {
  return (
    <>
      <main className="reveal mx-auto flex max-w-[1200px] flex-col px-6 md:px-8">
        <section className="grid items-end gap-x-12 gap-y-10 pt-12 pb-12 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-4">
              <Eyebrow className="text-primary">OnceSealed · carbon credit retirements</Eyebrow>
              <span aria-hidden className="h-px w-12 bg-primary/50" />
            </div>
            <h1 className="text-[52px] leading-[1.06] font-semibold tracking-[-0.025em] text-balance">
              Prove a credit was retired once,{" "}
              <span className="text-primary">without publishing who retired it.</span>
            </h1>
            <p className="max-w-[560px] text-lg leading-relaxed text-pretty text-muted-foreground">
              OnceSealed records each retirement on-chain as a serial range and a commitment hash. The buyer’s identity
              stays encrypted for an accredited auditor, and every project-quality finding cites the paragraph of the source document it came from.
            </p>
            <div className="flex flex-wrap gap-3">
              <TransitionLink href="/verify" className={buttonVariants({ variant: "primary" })}>
                Verify a retirement
              </TransitionLink>
              <TransitionLink href="/projects" className={cn(buttonVariants(), "bg-card/70 backdrop-blur-md")}>
                Browse project quality
              </TransitionLink>
            </div>
          </div>

          <figure className="flex flex-wrap items-center gap-x-6 gap-y-3 lg:justify-end lg:pb-24">
            <div className="flex items-start leading-none tabular-nums" aria-hidden>
              <span className="text-[120px] font-light tracking-[-0.05em]">{Math.round(ANONYMITY.undisclosed_share_2023_2026)}</span>
              <span className="mt-3 text-5xl font-light text-primary">%</span>
            </div>
            <figcaption className="flex max-w-[240px] flex-col gap-2 text-sm leading-snug">
              <span className="font-medium">
                of retired tonnes in 2023–2026 were explicitly marked ‘not disclosed’ or ‘anonymous’, up from{" "}
                {ANONYMITY.undisclosed_share_to_2018}% up to 2018.
              </span>
              <span className="text-[13px] text-muted-foreground">
                Our count over {ANONYMITY.snapshot};{" "}
                <a href={`${REPO_URL}/blob/main/${ANONYMITY.source}`} target="_blank" rel="noopener noreferrer">
                  method and lower-bound caveats
                </a>
                .
              </span>
            </figcaption>
          </figure>
        </section>

        <section aria-labelledby="pillars-h" className="flex flex-col gap-4 pb-16">
          <h2 id="pillars-h" className="sr-only">
            Three principles
          </h2>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-5">
            {PILLARS.map((p, i) => (
              <article
                key={p.n}
                style={staggerStyle(i)}
                className="animate-rise stagger flex flex-col gap-3.5 rounded-2xl border border-white/60 bg-card/75 p-6 shadow-[0_18px_40px_-24px_rgba(10,30,22,0.55)] backdrop-blur-md transition-[background-color,border-color,transform,box-shadow] duration-300 hover:-translate-y-[3px] hover:bg-card/90 dark:border-white/10"
              >
                <div className="flex items-center justify-between">
                  <span className={cn("grid size-10 place-items-center rounded-xl", p.tile)}>
                    <p.icon aria-hidden className="size-5" />
                  </span>
                  <span className="font-mono text-[13px] text-muted-foreground">{p.n}</span>
                </div>
                <h3 className="text-[22px] leading-snug font-semibold">{p.title}</h3>
                <p className="font-medium">{p.lead}</p>
                <p className="text-[14px] text-muted-foreground">{p.body}</p>
                <div className="mt-auto flex flex-wrap gap-x-5 gap-y-1">
                  {p.links.map((l) => (
                    <TransitionLink key={l.href} href={l.href} className="inline-flex min-h-11 items-center font-medium">
                      {l.label} →
                    </TransitionLink>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="screens-h" className="flex flex-col gap-5 pb-[72px]">
          <h2 id="screens-h" className="text-[26px] leading-tight font-semibold tracking-[-0.01em]">
            Explore the prototype
          </h2>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(480px,100%),1fr))] gap-3">
            {SCREENS.map((s, i) => (
              <TransitionLink
                key={s.href}
                href={s.href}
                style={staggerStyle(i)}
                className="animate-rise stagger flex min-h-11 items-center gap-5 rounded-2xl border border-border/80 bg-card/85 backdrop-blur-md px-6 py-5 text-foreground no-underline transition-[background-color,border-color,transform,box-shadow] duration-300 hover:-translate-y-[3px] hover:border-input hover:bg-secondary hover:text-foreground hover:shadow-[0_14px_30px_-18px_rgba(10,30,22,0.45)]"
              >
                <Badge tone={s.tone ?? "neutral"} className="min-w-32 justify-center">
                  {s.role}
                </Badge>
                <span className="flex min-w-0 flex-auto flex-col gap-0.5">
                  <strong className="font-semibold">{s.title}</strong>
                  <span className="text-sm text-muted-foreground">{s.body}</span>
                </span>
                <span aria-hidden className="text-muted-foreground">
                  →
                </span>
              </TransitionLink>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-card transition-colors duration-300">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-x-8 gap-y-4 px-8 py-7">
          <p className="max-w-[620px] text-[13px] text-muted-foreground">
            OnceSealed is a hackathon prototype on the Sepolia testnet. No real credits are retired: serials are
            simulated and buyers are fictional. Project scores are signals, not verdicts, and nothing here is investment
            or compliance advice.
          </p>
          <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2">
            <span className="text-[13px] text-muted-foreground">Registry contract</span>
            <HashChip value={NETWORK.contract} label="registry contract address" />
            <EtherscanLink hash={NETWORK.contract} kind="address">
              Sepolia Etherscan
            </EtherscanLink>
          </div>
        </div>
      </footer>
    </>
  );
}

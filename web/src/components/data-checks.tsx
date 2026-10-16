import { FileWarning } from "lucide-react";
import { DeterministicTag } from "@/components/quality";
import { Badge } from "@/components/ui/badge";
import { Callout, Card } from "@/components/ui/card";
import { CHECK_LABEL, CHECK_TONE, type Checks, DOCUMENT_ROLE, REPO_URL } from "@/lib/data";
import { formatInt, staggerStyle } from "@/lib/utils";

/** Deterministic checks of the documents against registry data, shown apart from the AI findings. */
export function DataChecks({ projectId, checks }: { projectId: string; checks: Checks }) {
  const results = checks.results.filter((c) => c.id !== "document_coverage");
  const read = checks.documents.map((d) => DOCUMENT_ROLE[d.role] ?? d.role).join(", ");
  const pages = checks.documents.reduce((n, d) => n + d.pages, 0);
  const tables = checks.documents.reduce((n, d) => n + d.tables, 0);

  return (
    <section aria-labelledby="checks-h" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div className="flex flex-col gap-1.5">
          <h2 id="checks-h" className="text-2xl leading-tight font-semibold tracking-[-0.01em]">
            Data checks
          </h2>
          <p className="text-muted-foreground">
            The document’s own figures against registry records (CarbonPlan OffsetsDB, {checks.offsetsdb_snapshot}).
            A flag is a lead for a reviewer, not a finding of wrongdoing.
          </p>
        </div>
        <DeterministicTag>Deterministic · not AI</DeterministicTag>
      </div>

      {checks.missing_documents.length > 0 && (
        <Callout tone="warn" icon={<FileWarning aria-hidden />}>
          <strong>Read: {read}</strong> ({formatInt(pages)} pages, {formatInt(tables)} tables).{" "}
          <strong>Not read:</strong> {checks.missing_documents.map((r) => (DOCUMENT_ROLE[r] ?? r).toLowerCase()).join(", ")}.
          Where the findings below say “no evidence”, the evidence may sit in a document that was not read.
        </Callout>
      )}

      <Card className="overflow-hidden">
        <ul>
          {results.map((c, i) => (
            <li
              key={c.id}
              style={staggerStyle(i)}
              className="animate-rise stagger flex flex-wrap items-start gap-x-6 gap-y-2 border-t border-border px-6 py-4 first:border-t-0"
            >
              <Badge tone={CHECK_TONE[c.status]} dot className="mt-0.5 min-w-28 justify-center">
                {CHECK_LABEL[c.status]}
              </Badge>
              <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-1">
                <h3 className="font-semibold">{c.title}</h3>
                <p className="text-[14px] text-pretty text-muted-foreground">{c.summary}</p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
      <p className="text-[13px] text-muted-foreground">
        Every number, page and table read is in{" "}
        <a href={`${REPO_URL}/blob/main/checks/${projectId}.json`} target="_blank" rel="noopener noreferrer">
          checks/{projectId}.json
        </a>
        .
      </p>
    </section>
  );
}

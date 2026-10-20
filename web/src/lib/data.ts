/**
 * Public data rendered by the static pages: the published quality reports, the ICVCM methodology
 * table, the simulated issuance batches and the Sepolia deployment. Generated from the repository by
 * `python scripts/export_web_data.py` (src/data/site.json); nothing here is sample data.
 */
import site from "@/data/site.json";

export type IcvcmStatus = "approved_with_conditions" | "not_approved" | "not_ccp_approved" | "under_assessment" | "unknown";

export const ICVCM_LABEL: Record<IcvcmStatus, string> = {
  approved_with_conditions: "Approved with conditions",
  not_approved: "Not approved",
  not_ccp_approved: "No CCP approval",
  under_assessment: "Under ICVCM assessment",
  unknown: "No ICVCM decision found",
};

export type PrincipleStatus =
  | "strong_evidence"
  | "partial_evidence"
  | "assertion_only"
  | "no_evidence"
  | "not_applicable"
  | "assessment_failed";

export const PRINCIPLE_LABEL: Record<PrincipleStatus, string> = {
  strong_evidence: "All checks found",
  partial_evidence: "Some checks found",
  assertion_only: "Assertion only",
  no_evidence: "No checks found",
  not_applicable: "Not applicable",
  assessment_failed: "Assessment failed",
};

/** Maps a principle status to a Badge / bar tone. */
export const PRINCIPLE_TONE = {
  strong_evidence: "ok",
  partial_evidence: "warn",
  assertion_only: "risk",
  no_evidence: "bad",
  not_applicable: "na",
  assessment_failed: "na",
} as const satisfies Record<PrincipleStatus, string>;

export const PRINCIPLE_ORDER: PrincipleStatus[] = [
  "strong_evidence",
  "partial_evidence",
  "assertion_only",
  "no_evidence",
  "not_applicable",
  "assessment_failed",
];

export const PRINCIPLE_NAME: Record<string, string> = {
  additionality: "Additionality",
  permanence: "Permanence",
  robust_quantification: "Robust quantification",
  no_double_counting: "No double counting",
  safeguards: "Sustainable development benefits and safeguards",
};

/** Short names for the checklist questions (core/ai/checklist.py); the full question is shown on hover. */
export const CHECK_NAME: Record<string, string> = {
  A1: "Financial analysis with a benchmark",
  A2: "Common practice",
  A3: "Not required by law",
  A4: "Carbon revenue considered early",
  P1: "Reversal risk assessed",
  P2: "Buffer contribution given",
  P3: "Measures against reversal",
  Q1: "Baseline calculation shown",
  Q2: "Leakage addressed",
  Q3: "Uncertainty or conservativeness",
  Q4: "Monitoring plan with parameters",
  D1: "Other GHG programs",
  D2: "Other credits or certificates",
  D3: "Host-country accounting",
  S1: "Stakeholder consultation details",
  S2: "Grievance mechanism",
  S3: "Environmental impact assessment",
  S4: "Community rights",
};

export type Evidence = { paragraph_id: string; page: number; text: string };

export type CheckAnswer = {
  id: string;
  question: string;
  answer: "yes" | "no" | null;
  evidence: Evidence[];
  second_opinion_p_yes: number | null;
  needs_review: boolean;
  dropped: string | null;
};

export type Principle = {
  principle: string;
  status: PrincipleStatus;
  score: number | null;
  rationale: string;
  dropped_findings: number;
  review_flags: string[];
  checks: CheckAnswer[];
  excerpt_chars: number | null;
  /** Paragraphs removed before any model read the excerpt because they read as instructions to an AI. */
  screened_out: { paragraph_id: string; page: number; matched: string }[];
};

/** A file the report read; paragraph ids from it start with `prefix` ("" for the project description). */
export type SourceDocument = { prefix: string; file_name: string; role: string };

export type Report = {
  hash: string;
  generated_at: string;
  document: { file_name: string; sha256: string; pages: number };
  documents: SourceDocument[];
  method: {
    llm_model: string;
    second_opinion_model: string | null;
    prompt_version: string;
    question_set_version: string;
    evidence_rule: string;
    excerpt_rule: string;
    injection_screen: string;
    methodology_table_version: string;
    pdf_extractor: string;
  };
  method_hash: string;
  methodology_status: {
    code: string;
    version: string | null;
    status: IcvcmStatus;
    summary: string;
    sources: string[];
    table_version: string;
  };
  overall: number;
  disclaimer: string;
  principles: Principle[];
};

/** One report version anchored on Sepolia; `file` is the archived report served by this site. */
export type Anchor = {
  version: number;
  tx: string;
  block: number;
  report_hash: string;
  generated_at: string;
  overall: number;
  schema: string;
  file: string;
};

export type Batch = {
  key: string;
  batch_id: `0x${string}`;
  vintage: number;
  batch_no: number;
  first_serial: number;
  last_serial: number;
  quantity: number;
  lot_size: number;
};

export type CheckStatus = "pass" | "flag" | "info" | "not_available";

export const CHECK_LABEL: Record<CheckStatus, string> = {
  pass: "Pass",
  flag: "Flag",
  info: "Info",
  not_available: "Not available",
};

export const CHECK_TONE = {
  pass: "ok",
  flag: "warn",
  info: "neutral",
  not_available: "ghost",
} as const satisfies Record<CheckStatus, string>;

/** Singular names of the document roles, for a single cited file. */
export const DOCUMENT_ROLE_ONE: Record<string, string> = {
  project_description: "Project description",
  validation_report: "Validation report",
  monitoring_report: "Monitoring report",
  verification_report: "Verification report",
  supporting: "Supporting document",
};

export const DOCUMENT_ROLE: Record<string, string> = {
  project_description: "Project description",
  validation_report: "Validation report",
  monitoring_report: "Monitoring reports",
  verification_report: "Verification reports",
  supporting: "Supporting document",
};

/** Deterministic data checks (scripts/run_checks.py): no model involved. */
export type Checks = {
  offsetsdb_snapshot: string;
  documents: { role: string; pages: number; tables: number }[];
  missing_documents: string[];
  results: { id: string; title: string; status: CheckStatus; summary: string }[];
};

export type Project = {
  id: string;
  name: string;
  country: string | null;
  category: string;
  doc_type: string | null;
  registry_url: string;
  methodology: string;
  methodology_version: string | null;
  reversal_risk: boolean | null;
  anchors: Anchor[];
  batches: Batch[];
  report: Report | null;
  checks: Checks | null;
};

export type Buyer = { name: string; lei: string; fictional: boolean };

export const NETWORK = site.network as {
  name: string;
  chain_id: number;
  contract: `0x${string}`;
  deploy_tx: string;
  deploy_block: number;
  explorer: string;
};
export const PROJECTS = site.projects as unknown as Project[];
export const BUYERS = site.buyers as Buyer[];
export const ANONYMITY = site.anonymity;
export const METHODOLOGY_TABLE_VERSION = site.methodology_table_version;

/** Accuracy of the report pipeline on the labelled gold set (scripts/eval_metrics.py), or null before labels. */
export const EVALUATION = site.evaluation as unknown as {
  questions: number;
  kappa: number;
  annotators: Record<string, string>;
  accuracy: number;
  accuracy_ci95: [number, number];
  label: string;
  per_question: Record<string, { n: number; correct: number }>;
  source: string;
  /** The citation check of the longer excerpts the reports read (scripts/citation_check_metrics.py). */
  long_excerpt: {
    questions: number;
    confirmed: number;
    confirmed_ci95: [number, number];
    judged_by: "human" | "ai";
    human_check: { annotator: string; units: number; agree: number } | null;
    source: string;
  } | null;
  /** Label-free robustness tests (scripts/robustness_tests.py). */
  robustness: {
    screen: string;
    source: string;
    evidence_removed: RobustnessResult;
    irrelevant: RobustnessResult;
    inject_yes: Record<string, RobustnessResult>;
    inject_no: RobustnessResult;
  } | null;
} | null;

type RobustnessResult = {
  questions: number;
  right_before: number;
  changed_by_test: number;
  as_expected: number;
  screen_catches_it?: boolean;
};

/** The file a cited paragraph comes from: extra files give their paragraph ids an "x<k>-" prefix. */
export function sourceOf(report: Report, paragraphId: string) {
  return report.documents.find((d) => d.prefix && paragraphId.startsWith(d.prefix)) ?? report.documents[0];
}
export const REPO_URL = "https://github.com/lsaliherenl/OnceSealed";

export function getProject(id: string) {
  return PROJECTS.find((p) => p.id.toLowerCase() === id.toLowerCase());
}

export function projectOfBatch(batchId: string) {
  for (const p of PROJECTS) {
    const b = p.batches.find((x) => x.batch_id.toLowerCase() === batchId.toLowerCase());
    if (b) return { project: p, batch: b };
  }
  return undefined;
}

export function principleCounts(p: Project) {
  const counts: Partial<Record<PrincipleStatus, number>> = {};
  for (const x of p.report?.principles ?? []) counts[x.status] = (counts[x.status] ?? 0) + 1;
  return counts;
}

export function buyerName(lei: string) {
  return BUYERS.find((b) => b.lei === lei.toUpperCase())?.name;
}

/** "SIM-VCS1477-2015-001-000001001" — simulated, Verra-like; not a real registry serial. */
export function serialLabel(b: Pick<Batch, "key">, serial: number) {
  return `SIM-${b.key.replaceAll("|", "-")}-${String(serial).padStart(9, "0")}`;
}

export function rangeLabel(b: Pick<Batch, "key">, start: number, end: number) {
  return `${serialLabel(b, start)} → ${String(end).padStart(9, "0")}`;
}

/** Parses "SIM-VCS1477-2015-001-000001500" (or "VCS1477|2015|001 1500") into a batch and serial. */
export function parseSerial(input: string) {
  const s = input.trim().toUpperCase();
  const m = s.match(/^(?:SIM-)?([A-Z]+\d+)[-|](\d{4})[-|](\d{3})[-|\s]+0*(\d+)$/);
  if (!m) return undefined;
  const key = `${m[1]}|${m[2]}|${m[3]}`;
  const project = PROJECTS.find((p) => p.id === m[1]);
  const batch = project?.batches.find((b) => b.key === key);
  if (!project || !batch) return undefined;
  return { project, batch, serial: Number(m[4]) };
}

export type AuditStatus = "pending" | "verified" | "rejected";

export const AUDIT_LABEL: Record<AuditStatus, string> = {
  pending: "Pending",
  verified: "Verified",
  rejected: "Rejected",
};

export const AUDIT_TONE = {
  pending: "warn",
  verified: "ok",
  rejected: "bad",
} as const satisfies Record<AuditStatus, string>;

/** Contract enum AuditStatus { Pending, Verified, Rejected }. */
export const AUDIT_FROM_CHAIN: AuditStatus[] = ["pending", "verified", "rejected"];

/** The auditor's checks (core/privacy/vault.py `audit`): [title, pass detail, fail detail]. */
export const AUDIT_CHECKS: Record<string, [string, string, string]> = {
  vault_found: ["Vault found", "The encrypted vault for this retirement is stored.", "No vault stored for this retirement."],
  vault_hash_matches_chain: [
    "Vault hash matches the chain",
    "keccak256 of the stored ciphertext equals the vault hash recorded on-chain.",
    "The stored ciphertext is not the one recorded on-chain.",
  ],
  vault_opens: ["Vault opens with the auditor key", "Decrypted with the auditor's private key.", "Decryption failed."],
  range_matches_chain: [
    "Serial range matches the chain",
    "Batch and range in the vault equal the on-chain record.",
    "The vault names a different batch or range.",
  ],
  lei_valid: ["LEI valid (ISO 17442)", "20 characters with valid check digits.", "LEI structure or check digits invalid."],
  buyer_id_matches_lei: [
    "Buyer id matches the LEI",
    "keccak256(\"LEI:\" + LEI) equals the buyer id in the vault.",
    "The buyer id was not derived from this LEI.",
  ],
  commitment_matches_chain: [
    "Commitment opens",
    "Recomputed from buyer id, salt, batch and range; equals the on-chain commitment.",
    "Recomputed commitment differs from the on-chain commitment.",
  ],
};

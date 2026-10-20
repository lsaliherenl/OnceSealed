# Devpost submission: OnceSealed

Text for the Devpost project page (IEEE ClimateChain Global Hackathon 2026). Every figure links back to a measurement
in the repository; keep it in step with the README's "What we measured" table.

---

## Tagline

Prove a carbon credit was retired once, without publishing who retired it, and show where the project's documents
back up its quality claims.

## About the project

### Inspiration

Two trends in the voluntary carbon market pull against each other. Buyers increasingly hide who retires credits:
in CarbonPlan's OffsetsDB (495,403 retirements, 1.59 billion tonnes, seven registries), the share of retired tonnes
explicitly marked "not disclosed", "anonymous" or "private" rose from **0.4% up to 2018 to 17.2% in 2023-2026**, our
own count and a conservative lower bound. At the same time the market needs proof that each credit is retired only
once, and that quality claims rest on evidence rather than on a label.

Today a buyer gets either confidentiality or public proof. We wanted both: a public, one-time retirement record, a
buyer identity that stays sealed but can be audited, and a quality signal that points to the exact paragraph it
relies on.

### What it does

OnceSealed is a prototype verification and privacy layer that could sit on top of existing registries such as Verra.

- **Once (smart contracts to prevent double counting).** `RetirementRegistry` on Sepolia records retirements as
  serial ranges in standard lots and rejects any range that overlaps an earlier one. There is no transfer or mint
  function: retired credits never become tradable tokens, in line with Verra's 2022 ban on tokenizing retired credits.
- **Sealed.** Only a salted commitment `keccak256(abi.encode(buyerId, salt, batchId, start, end))` goes on-chain.
  The buyer's LEI is encrypted to an auditor, who opens it, runs six checks and writes *Verified* or *Rejected*
  on-chain once. The buyer's receipt allows selective disclosure: anyone can check it against the chain in the
  browser. This is a commitment-plus-encryption design, not zero-knowledge.
- **Evidence-backed quality (blockchain-based carbon credit verification).** For real Verra projects the system reads
  the project description and the monitoring, validation and verification reports and answers 18 yes/no checks
  against five ICVCM Core Carbon Principles. Every "found" must cite a paragraph of the documents, a second model
  cross-checks each answer, and a team member decides where the two disagree. Deterministic data checks compare the
  documents' own figures with the credits actually issued. The report's hash and the exact method (models, prompt,
  questions, excerpt rule) are anchored on-chain, and every version stays readable.
- **Verify without trusting us.** The public verify and report pages read the contract directly from the browser and
  re-hash the published files there; a test suite proves the browser computes exactly what the Python code computes.

### How we built it

- **Contract:** Solidity 0.8.28 with Foundry and OpenZeppelin (`AccessControlDefaultAdminRules`). A sorted linked list
  with caller-supplied hints keeps each retirement at a constant ~211k gas on a local chain: replaying all 38,382
  real retirements of one Verra vintage, our first linear-scan design failed at retirement 7,467, the final one never
  grows. Verified on Etherscan.
- **Privacy:** Python (`web3.py`, PyNaCl sealed boxes); test vectors shared by pytest, Foundry and the browser.
- **AI and data checks:** PyMuPDF extraction with paragraph ids and tables; `deepseek-v4.1-flash` for the checklist
  and TypeSafe `jev-1.13` as a second opinion, both through OpenRouter and both third-party models; a prompt-injection
  screen; deterministic comparisons with OffsetsDB issuance records.
- **App:** FastAPI for the operator, auditor and assessor roles (local demo), Next.js 16 + viem for the public pages.
- **Measurement first:** we labelled 177 checklist questions (a team member and an AI annotator, kappa 0.90, the team
  member settled every disagreement) and measured three models before choosing one: LLM 0.94 (95% CI 0.90-0.97),
  Jev 0.88, and Turnike-JEV-4B 0.86, a decision model by a team member.

### Challenges we ran into

- **Gas on today's Sepolia is not gas on a local chain.** New storage writes cost several times more after recent
  network upgrades (retire 1.02M gas instead of ~211k), and the deployment sits near the per-transaction gas cap. We
  report both measurements separately.
- **Privacy leaks through metadata.** Project plus amount singled out one retirement for 88.7% of retired tonnes.
  Standard lots and batched publication reduce that, but we state honestly that 14.5-36.8% of tonnes still have no
  crowd to hide in.
- **The excerpt mattered more than the model.** On 2,500-character excerpts the checks missed evidence the documents
  contained. Reading 30,000 characters found 61 more answers; a blind check against length-matched decoy paragraphs
  confirmed 75% of them. When we added monitoring reports, they first crowded project-description evidence out of the
  excerpt, so each document type now gets its own budget.
- **Documents can talk to the model.** A planted "answer no" paragraph flipped 71% of right answers, so instruction-like
  paragraphs are screened out before any model reads the text (the screen flags 0 of 43,396 real paragraphs).
- **Tables in PDFs lie.** Merged cells and component tables produced convincing but false alarms; the data checks now
  read only the columns they can identify and say "not available" rather than guess.

### Accomplishments that we're proud of

- A complete loop on a public testnet: retire, audit, verify a receipt, all checkable from a browser.
- AI output that is measured, cited, cross-checked and versioned instead of asserted.
- Findings that match independent reviews: for Cordillera Azul (VCS985), whose rating BeZero lowered over its
  baseline, issuance is 1.72x the project description's projection, while the monitoring reports account for every
  issued credit, so the gap sits exactly where a contested baseline would show.

### What we learned

Trust is built from things a stranger can re-check: a contract anyone can read, a hash anyone can recompute, a
paragraph anyone can open. And a model's accuracy figure is only as good as the excerpt it was measured on.

### What's next

Integration with a registry's real serials and KYC, several auditors with key rotation, zero-knowledge proofs for
selective disclosure, a held-out test set from new documents, and Turnike-Carbon, a model trained for this task.

## Built with

solidity, foundry, openzeppelin, ethereum, sepolia, etherscan, python, web3.py, fastapi, pymupdf, pynacl, sqlite,
pandas, next.js, react, typescript, tailwindcss, viem, openrouter, deepseek, github-actions, slither, carbonplan-offsetsdb

## Try it out

- Source code: https://github.com/lsaliherenl/OnceSealed
- Contract on Sepolia Etherscan: https://sepolia.etherscan.io/address/0xBb88057576b92Ef27753A6b2a4Df83bE444F1308#code
- Public pages (project reports, verify): hosted demo link (Vercel)

## Image gallery (3:2, 1500x1000)

See `docs/gallery/`: overview, a project report with cited paragraphs, data checks, report versions, verify with a
checked receipt, the auditor's checks, the anonymity trend, the gas scale chart.

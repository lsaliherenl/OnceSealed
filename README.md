# OnceSealed

**Confidential but auditable carbon credit retirement, with evidence-backed quality signals.**

> **Status: work in progress (draft README).** Built for the IEEE ClimateChain Global Hackathon 2026,
> track *Improve trust, transparency, and efficiency in carbon markets*. Sections marked **TODO** are not built yet.

OnceSealed is a prototype verification and privacy layer that could sit on top of existing carbon registries:

- **Once:** every credit can be retired only once. Overlapping serial ranges are rejected by a smart contract.
- **Sealed:** the buyer's identity is never written on-chain. Only a salted commitment is public; an authorized
  auditor can open an encrypted vault and attest on-chain that the commitment is correct.
- **Evidence-backed quality:** project documents are assessed against ICVCM Core Carbon Principles. Every finding
  quotes the source document verbatim, and code checks each quote against the PDF before it counts.

> **This is not a real registry and performs no real retirements.** Real retirements happen in official registries
> such as Verra. OnceSealed uses real project data and simulated serial numbers to show how such a layer would work.

---

## The problem

Companies increasingly hide who retires carbon credits ("greenhushing"), while the market needs auditability.

Our analysis of 495,000 retirement records (1.59 billion tonnes, 7 registries) in CarbonPlan's OffsetsDB
([full method and tables](docs/anonymity_stats.md)):

- Retired tonnes **explicitly marked "not disclosed", "not public" or "anonymous" rose from 0.4% (up to 2018) to 17.2%
  (2023–2026)**.
- In 2023–2026, **53–55%** of retired tonnes name no identifiable beneficiary at all.

![Explicitly undisclosed retirements are rising](docs/figures/anonymity_trend.png)

The tension: buyers want confidentiality; regulators, auditors and the public want proof that each credit was
retired exactly once and that its quality claims are grounded in evidence.

## How it works

### 1. Quality assessment (three layers)

| Layer | What it does | AI? |
|---|---|---|
| **Methodology status** | Looks up the ICVCM decision for the project's methodology in a sourced, versioned table ([`core/ai/methodology_status.json`](core/ai/methodology_status.json)). | No |
| **Evidence extraction** | An LLM (`deepseek/deepseek-v4.1-flash` via OpenRouter) reads the relevant parts of the project document and returns verbatim quotes per principle. Code verifies every quote against the PDF text; unverifiable quotes are dropped. | Yes |
| **Evidence judgement** | A decision model answers closed questions about the verified evidence and returns probabilities. Currently **TypeSafe Jev 1.13** (third-party model via OpenRouter). The model sits behind a swappable interface so other decision models can be evaluated on the same question set. | Yes |

Principles assessed (5 of ICVCM's 10, the ones a project document can evidence): additionality, permanence,
robust quantification, no double counting, social and environmental safeguards.

The report is published as JSON in [`reports/`](reports/). Its `keccak256` hash over canonical JSON, plus a
`method_hash` that pins the models and question set used, are anchored on-chain, so anyone can re-hash the
published file and compare.

> **Signal, not verdict.** Scores describe how well the submitted document evidences each principle. They are not an
> ICVCM assessment, a rating of the project, or a statement about its real-world climate impact.

### 2. Confidential retirement

1. The registry operator retires a serial range on-chain with
   `buyerCommitment = keccak256(abi.encode(buyerId, salt, batchId, start, end))`, where `salt` is 32 random bytes and
   `buyerId = keccak256("LEI:" + LEI)`. A purchase is retired as standard lots (1,000 t in the demo), each with its own
   salt, so the amount and the lots of one purchase cannot be linked on-chain (see the limits below).
2. `{serial range, LEI, buyerId, salt}` is encrypted to the auditor's public key (libsodium sealed box) and stored
   off-chain; only `keccak256(ciphertext)` goes on-chain.
3. The auditor decrypts, recomputes both hashes, and records an attestation on-chain.
4. The buyer can selectively disclose by sharing the salt; anyone can check it with the `verifyClaim` view function.

**Threat model:** privacy is against the public, not against the registry (which already knows its account holders).
This is a hash commitment + encryption design, **not** a zero-knowledge proof system.

### 3. Smart contract

[`RetirementRegistry`](contracts/src/RetirementRegistry.sol) (Solidity 0.8.28, OpenZeppelin AccessControl):

| Function | Role | What it does |
|---|---|---|
| `registerBatch` | operator | Declares an issuance batch, its serial range and its lot size (0 = free ranges). |
| `registerQualityReport` | assessor | Anchors a report hash, score and method hash; versions are kept. |
| `retire` | operator | Retires serials `[start, end]`; rejects any range that overlaps a previous retirement (`AlreadyRetired`). In a lot batch the range must be exactly one aligned lot (`NotALot`). Records the project's report version at that moment. |
| `attestRetirement` | auditor | One-time, final `Verified` / `Rejected` status after checking the vault off-chain. |
| `verifyClaim` | anyone (view) | Checks a disclosed `(buyerId, salt)` against the commitment. |

The commitment is `keccak256(abi.encode(buyerId, salt, batchId, start, end))`, so a disclosed salt proves exactly one
retirement and cannot be reused for another. There is no transfer or mint function: retired credits cannot become
tradable again.

Tested with Foundry (46 tests, including fuzz tests that check, over thousands of random ranges and hints, that no
serial is ever retired twice). Overlap checks cost the same however many retirements a batch has: lot batches look
up the lot index directly, and free-range batches keep a sorted linked list where the caller passes the predecessor
as a hint (a wrong hint can only make the call revert). A first version scanned the list linearly; replaying 38,382
real retirements of one Verra batch, it hit the block gas limit at retirement 7,467
([scale results](data/derived/scale/summary.json), [chart](docs/figures/scale_gas.png)).

**Privacy limits, measured** ([threat model](docs/threat_model.md), T12): for 88.7% of retired tonnes in OffsetsDB,
project + quantity alone single out one retirement. Standard lots remove the quantity; timing still links lots unless
the operator publishes them in shuffled periodic batches, and even then 14.5% (quarterly) to 36.8% (daily) of tonnes
have no other purchase in the same project and period to hide among.

## Design decisions

- **Retired credits never become tradable tokens.** The chain only stores proof records. Verra
  [prohibited](https://verra.org/verra-bans-greenwashing-cryptos-using-retired-credits/) tokenizing retired credits in 2022.
- **No personal data on-chain:** only hashes, commitments, scores and serial ranges.
- **Every AI finding must quote the document verbatim**, and the quote must be found in the PDF by code.
- **AI scores are signals, not verdicts**, and are shown next to the deterministic methodology status.
- **Honest model attribution:** each report records which models produced it.

## Current results (draft)

Reports for four real Verra projects (project documents are not redistributed; see [`samples/manifest.json`](samples/manifest.json)):

| Project | Methodology (ICVCM status) | Overall evidence signal |
|---|---|---|
| VCS1851 grid-connected solar, India | ACM0002 (not approved, additionality) | see [`reports/VCS1851.json`](reports/VCS1851.json) |
| VCS138 landfill gas, USA | ACM0001 v16 (approved with conditions) | see [`reports/VCS138.json`](reports/VCS138.json) |
| VCS1477 Katingan REDD+, Indonesia | VM0007 (no CCP approval; successor VM0048 approved) | see [`reports/VCS1477.json`](reports/VCS1477.json) |
| VCS2505 cookstoves, South Africa | VMR0006 (no CCP approval; successor VM0050 approved) | see [`reports/VCS2505.json`](reports/VCS2505.json) |

So far every quote returned by the LLM was found in the source PDF. **We make no accuracy claim yet:** a human-labelled
evaluation set is planned (**TODO**).

## Repository layout

```
contracts/      Foundry project: RetirementRegistry + tests
core/ai/        PDF extraction, quote verification, LLM client, decision model, report builder
core/privacy/   buyer identities (LEI), commitments, sealed-box audit vault, receipts
core/chain/     web3.py client, deployment records, committed ABI
core/service.py end-to-end flows used by the app (retire, audit, verify a receipt)
core/hashing.py canonical JSON + keccak256
scripts/        assess_project.py (build a report), jev_smoke_test.py (evidence extraction only)
tests/          unit tests (no API calls) + vectors.json shared with the Foundry tests
reports/        published quality reports
data/evidence/  verified evidence + question set per project (for evaluating other decision models)
samples/        manifest of demo documents (URLs + SHA-256); PDFs are downloaded manually
```

## Quick start

Requirements: Python 3.11+ (tested on 3.14), [Foundry](https://getfoundry.sh) for the contracts.

```bash
git clone --recurse-submodules <repo-url>
cd OnceSealed
python -m venv .venv
.venv/Scripts/activate          # Windows; use `source .venv/bin/activate` on macOS/Linux
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python -m pytest -q             # unit + end-to-end tests, no API key needed (end-to-end needs Foundry's anvil)
python scripts/demo_e2e.py      # full flow on a throwaway local chain: retire, overlap rejected, audit, disclosure
```

To regenerate a report you need an OpenRouter API key in `.env` (copy `.env.example`) and the project PDF in
`samples/pdfs/` (download it manually from the Verra registry link in `samples/manifest.json`):

```bash
python scripts/assess_project.py VCS1851
```

## Data sources and attribution

- **[CarbonPlan OffsetsDB](https://carbonplan.org/research/offsets-db)** — project, issuance and retirement data from
  ACR, ART, CAR, Cercarbono, Gold Standard, Isometric and Verra. Snapshot generated 2026-06-01. Used under the
  [OffsetsDB Terms of Data Access](https://offsets-db-data.readthedocs.io/en/stable/TERMS-OF-DATA-ACCESS.html);
  CarbonPlan claims no copyright in the data, and the underlying records belong to the registries.
- **[Verra Registry](https://registry.verra.org)** — public project documents (not redistributed in this repository).
- **[ICVCM Core Carbon Principles](https://icvcm.org/?p=2349)** and ICVCM methodology decisions (sources listed per
  entry in `core/ai/methodology_status.json`).
- **Models:** `deepseek/deepseek-v4.1-flash` and TypeSafe `jev-1.13`, both accessed through [OpenRouter](https://openrouter.ai).
  Neither model was developed by this team.

## Limitations

- Simulated retirements and serial numbers; no integration with a real registry.
- Quality signals depend on what the project document says; they cannot detect misreporting that is internally consistent.
- LLM and decision-model outputs vary slightly between runs; the on-chain hash pins the exact published report.
- Decision-model confidence values are not calibrated against labelled data yet.

## Roadmap

- [x] `RetirementRegistry` contract + Foundry tests
- [x] Sepolia deployment + Etherscan verification: [`0xBb88…1308`](https://sepolia.etherscan.io/address/0xBb88057576b92Ef27753A6b2a4Df83bE444F1308#code) (demo transactions in `deployments/11155111-seed.json`)
- [x] Privacy module (commitments, sealed-box audit vault) with Python ↔ Solidity test vectors
- [x] Python chain client and end-to-end flow on a local chain (`scripts/demo_e2e.py`)
- [ ] Streamlit app: buyer, public verification, auditor and project quality views
- [x] Anonymity statistic from OffsetsDB ([docs/anonymity_stats.md](docs/anonymity_stats.md))
- [x] Issuance batches from real OffsetsDB issuance records (`data/batches.json`, simulated serials)
- [ ] Human-labelled evaluation set; compare decision models on it
- [ ] Demo video

## License

[MIT](LICENSE)

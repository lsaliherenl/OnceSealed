# Threat model and security review

What OnceSealed protects, from whom, what it does not protect, and how each claim is tested.
Numbers come from the scripts named next to them; tests are in `contracts/test/` and `tests/`.

## Assets and parties

| Party | Holds | Trusted for |
|---|---|---|
| **Registry operator** (e.g. Verra) | operator key; sees the buyer at retirement time (KYC) | recording retirements honestly; it already knows its account holders |
| **Buyer** | the retirement receipt (contains the salt) | deciding whether to disclose |
| **Auditor** | auditor role key; private key of the vault | checking vaults and attesting truthfully |
| **Assessor** | assessor role key | anchoring the published quality report |
| **Admin** | default admin role | granting and revoking roles |
| **Public** | read access to the chain | nothing; everything they see must be verifiable |

**Privacy goal:** the public cannot learn who retired a credit unless the buyer discloses it. Privacy is **against the
public, not against the registry**, which knows its customers anyway. This is hash commitments plus encryption, not
zero-knowledge proofs.

## Scenarios

| # | Scenario | What happens | Evidence |
|---|---|---|---|
| T1 | Someone without a role writes to the registry | Reverts with `AccessControlUnauthorizedAccount`; the API also refuses writes without a role token | `test_RevertWhen_CallerLacksRole`, `tests/test_api.py` |
| T2 | Same serials retired twice (double counting) | Rejected with `AlreadyRetired(id)`; fuzzing over thousands of random ranges never produced a serial covered twice | `testFuzz_NoSerialRetiredTwice`, `testFuzz_SecondRetirementRevertsIffOverlap` |
| T3 | Operator passes a wrong or malicious `prevHint` | The call reverts (`InvalidHint` or `AlreadyRetired`); a hint can never let an overlapping range in | `testFuzz_AnyHintNeverAllowsDoubleRetirement` |
| T4 | Operator key stolen | Admin revokes the role; later writes fail, past records are untouched (the contract has no delete or edit) | `test_RevokedOperatorCannotRetire` |
| T5 | Admin key stolen or a mistaken admin transfer | Admin handover is two-step with a delay (2 days by default); one transaction cannot transfer control; the admin role cannot be granted directly | `test_AdminHandoverIsTwoStepWithDelay`, `test_AdminRoleCannotBeGrantedDirectly` |
| T6 | Dishonest operator: commitment for buyer A, vault naming buyer B | Auditor's check fails (`commitment_matches_chain = false`) and the retirement is marked **Rejected** on-chain, permanently | `test_auditor_rejects_vault_that_does_not_match_commitment` |
| T7 | Vault replaced or tampered off-chain | `keccak256(ciphertext)` no longer matches `auditVaultHash` on-chain; sealed box authentication fails | `test_audit_detects_tampered_ciphertext` |
| T8 | Disclosed salt reused to claim another retirement | Commitment is bound to `(batchId, start, end)`; the claim fails | `test_DisclosedSaltCannotClaimAnotherRetirement`, API forged-receipt test |
| T9 | Brute-forcing the buyer from the commitment | Infeasible: 256-bit random salt per retirement; two retirements by the same buyer are unlinkable | design (`core/privacy/commitment.py`) |
| T10 | **Dishonest auditor** attests a vault it did not check, or rejects a valid one | **Not prevented.** A single auditor is a single point of trust; attestations are final and public, so the auditor is accountable but not checked | limitation; see mitigations |
| T11 | **Auditor loses the vault key** | **Vaults become unreadable**; on-chain records and selective disclosure by buyers still work | limitation; see mitigations |
| T12 | **Linking a retirement through public metadata** | **Partly possible** - see the measurement below | `scripts/linkability_stats.py` |
| T13 | Registry outside this layer retires the same credits again | Not detectable here: the layer only sees what the registry records through it | out of scope; integration path in README |

## T12 in numbers: how identifying is the on-chain metadata?

The chain shows project, serial range (hence quantity) and time, but no name. If a company publishes
"we retired N tonnes from project X" (as many sustainability reports do), can the on-chain record be matched?
Measured on all 495,403 retirements in OffsetsDB (snapshot 2026-06-01) with `scripts/linkability_stats.py`:

| Public information about a retirement | Share of retirements that are unique | Share of tonnes in unique retirements |
|---|---|---|
| project + quantity | 30.6% | **88.7%** |
| project + quantity + month | 48.2% | 93.9% |
| project + quantity + day | 60.4% | 94.5% |
| project + day | 22.0% | 31.6% |

**Interpretation.** The commitment hides the name, but a distinctive quantity can give the buyer away if the buyer
(or someone else) publishes it. For 88.7% of retired tonnes, project and quantity alone single out one retirement.

**Mitigation, now enforced by the contract: standard lots.** A batch can be registered with a lot size
(`registerBatch(..., lotSize)`, 1,000 t for the demo batches). In such a batch every retirement must be exactly one
aligned lot (only the batch's final lot may be shorter), and each lot gets its own salt and commitment. A purchase
of 5,000 t appears on-chain as five identical-looking lots, so the quantity no longer points at a buyer. Amounts
that are not whole lots cannot be retired privately in a lot batch.

| Lot size | Tonnes in whole lots | Tonnes in remainders (not private) |
|---|---|---|
| 100 t | 99.4% | 0.6% |
| 1,000 t | 95.8% | 4.2% |
| 10,000 t | 78.4% | 21.6% |

**But timing still links lots.** An earlier version of this document quoted a "median anonymity set of 61 lots"
(the median number of lots per project). That ignored time: a buyer's five lots are retired together, so if
nobody else retires from the same project around then, the lots are trivially grouped. We therefore model an
operator that publishes all lots of a project once per epoch, in shuffled order. The anonymity set of a purchase is
the number of purchases (OffsetsDB retirement records) with lots in the same project and epoch:

| Lots of 1,000 t, published once per | Median anonymity set | Tonnes with no other purchase (fully exposed) | Tonnes in sets of >= 5 | Tonnes in sets of >= 10 |
|---|---|---|---|---|
| day | 2 | 36.8% | 17.0% | 4.6% |
| week | 2 | 30.5% | 22.9% | 7.2% |
| month | 3 | 21.4% | 35.4% | 15.2% |
| quarter | 5 | 14.5% | 49.7% | 27.4% |

**Interpretation.** Lots plus batched publication cut the exposed share from 88.7% of tonnes (project + quantity)
to 14.5-36.8%, depending on how long the operator waits. They cannot do better than the crowd: when a project has
only one buyer in a period, any record that shows the project and the period exposes that buyer. Hiding the project
itself would need zero-knowledge proofs (future work). The epoch-based publication is an operating rule for the
registry, not something the contract can enforce; the contract enforces the lot rule.

## Mitigations for the open limitations (future work, not implemented)

- **T10 dishonest auditor:** k-of-n auditors (several auditors must attest), or a regulator able to re-open an audit.
- **T11 key loss:** seal each vault to two keys (auditor and a regulator escrow key) and support key rotation by
  re-sealing vaults to a new key with an on-chain record of the key version.
- **T12 linkability:** standard lots are enforced on-chain; batched publication per epoch is an operator rule
  (measured above). Longer term, zero-knowledge proofs of "this retirement belongs to an entity in sector S"
  without revealing project, quantity or identity.

## Static analysis (Slither 0.11.6)

Run: `slither contracts --filter-paths "lib/|test/"` (102 detectors).

| Finding | Assessment |
|---|---|
| `uninitialized-state`: `_batchRetirements` "never initialized" | False positive (array pushed through a local storage reference). Code simplified to push directly; the finding is gone. |
| `timestamp` in `hintFor` | False positive: the comparison is between serial numbers (`start`), not timestamps; Slither flags it because the struct also stores `retiredAt`. |
| `cyclomatic-complexity` of `retire` (12) | Informational. Every branch is a distinct safety check and is covered by unit and fuzz tests. |

No other findings. Foundry's linter (`forge build`) reports no warnings.

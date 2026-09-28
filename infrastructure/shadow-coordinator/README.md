# Read-only Shadow Coordinator (#3)

Run once in the persistent CODEX workspace with Python 3.11+ and GitHub CLI:

```sh
python3 infrastructure/shadow-coordinator/shadow.py --issue 1724 --pr 1733
```

Explicit issue selection is required; the PR is optional and, when selected,
is treated as a caller-selected observation pair, not verified canonical linkage.
This does not establish exclusive canonical lineage or authority. No repository-wide crawler, scheduler, agent/CI
dispatch, Suite writer, database, cache or journal exists. Output is advisory
JSON on stdout. Exit 2 means unknown/incomplete evidence; exit 0 includes
blocked/waiting/terminal observations and never means permission to mutate.

The only transport is `gh api --method GET`, fixed to `Innovestro/aidumo-suite`.
Use read-only Contents, Issues, Pull requests, Checks and Commit statuses access.
The standing executor token can run it, but broader credential possession cannot
activate writes. Missing access fails closed. Never put credentials in arguments,
fixtures or this checkout. Redirected observations belong outside the checkout;
normal output includes identifiers/hashes rather than source bodies or diagnostics.

Each invocation reads current main and verifies the hashes in `contracts.json`
against these Suite-owned contracts: WORK_CLAIM_POLICY, AGENT_EXECUTION_POLICY,
OPERATIONAL_ADMISSION_GATES and the canonical work_claim resolver. These were
reviewed at Suite `dcdea09ffd16cb20485d369772aac018451483de`. The adapter compiles
only the resolver's reviewed pure prefix (before line 741), excluding network,
CLI and writer definitions/imports. Hash mismatch blocks before compilation.
Contract updates require a fresh B adapter review; changing pins is not automatic.
Suite claim semantics remain in Suite, including server comment-ID ordering,
race winners, lease expiry, scheduled/direct identities and terminal history.

Complete paginated selected issue/PR comments, reviews, exact-head check runs and
commit statuses are read twice; disagreement or main movement returns unknown.
Each list is bounded at 2,000 records and truncation fails closed. This is an
observation consistency check, not an atomic GitHub snapshot or a write fence.
Checks read denial is retained as missing evidence alongside the reconstructed
issue/PR/claim state. No cached result is reused. Head and base are explicit and
part of the evidence digest. Every restart rebuilds from GitHub. Equal evidence
and equal lease-validity intervals yield equal decisions; time crossing a lease
expiry correctly changes the claim projection even if no comment changed.
Duplicate equal IDs collapse; conflicting duplicates fail closed. Input order
never changes canonical comment-ID resolution.

Projection deliberately grants no write operation. A known Suite blocking label
blocks; closed issues produce no new operation; valid active generic claims
project waiting for their holder; current-head pending checks project waiting for
qualification. Invalid/missing authority and vendor queue provenance not proven
by this bounded adapter remain unknown. Green checks, labels, author identity and
claim possession never imply DEV PASS, Product acceptance, complete required
qualification, or admission. Reviews and comment evidence contribute to the
fingerprint but free-text authority is not guessed. Global capacity, external
human decisions and all linked Product dependencies are not crawled: a new
lineage start or integration can therefore never be projected as authorized.

Tests use an external read-only Suite checkout containing the pinned contracts:

```sh
SUITE_CHECKOUT=/path/to/aidumo-suite python3 -m unittest discover \
  -s infrastructure/shadow-coordinator -v
```

No test needs credentials or writes to Suite. For a live smoke, select one
non-sensitive issue/PR explicitly and run the command twice in fresh processes.
Record evidence and limits in the canonical B PR, not a local readiness ledger.
This capability runs directly from reviewed source and needs no host deployment.

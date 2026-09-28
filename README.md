# Aidumo Development Infrastructure (B)

This repository owns the executable development infrastructure for Aidumo.
B0 and B1 are integrated. The current B1 follow-up is
[#10: standing GitHub access](https://github.com/Innovestro/aidumo-development-infrastructure/issues/10).
The [runtime and Owner runbook](infrastructure/codex-unraid/README.md) describe
one persistent Unraid CODEX container and standing credentials for B and Suite.
The Owner-chosen PAT is not repository-restricted; credential reach does not
authorize work. Only explicitly admitted packages may be executed under their
repository governance. The [Linux VM runbook](infrastructure/linux-vm/README.md)
records #5's proven Owner-operated baseline reset; there is no coordinator or VM
automation here.

## Authority and sources

| System | Owns | Does not own |
| --- | --- | --- |
| **A — [aidumo-suite](https://github.com/Innovestro/aidumo-suite)** | Canonical Product/Suite contracts, Suite work, claims, readiness, review and release semantics, and Suite-specific qualification requirements. | B host/runtime implementation or C tester implementation. |
| **B — this repository** | Development-infrastructure source/configuration and its own implementation issues and PRs; later, explicitly authorized execution and host/runtime capabilities. | Product truth, Product/PM/DEV approval authority, a second Suite issue/claim/readiness/review queue, or automatic merge/release authority. |
| **C — [aidumo-external-tester](https://github.com/Innovestro/aidumo-external-tester)** | Separate outside-in evidence producer: journeys, personas/test worlds, seed/reset lifecycle, Run Manifest/Result state, browser-runner security/admission and evidence retention. | General development infrastructure or Product/PM/DEV/release approval authority. |

Human Product/Owner authority determines Product semantics, priority, supported
states, Engineering Envelopes, assurance depth and mechanism budgets. AI Product
Steward, DEV and executors operate within that authority; B cannot grant it.
Shared hardware does not merge A/B/C authority or credentials. C remains separately
authorized through [Suite #593](https://github.com/Innovestro/aidumo-suite/issues/593).

The durable sources are:

- [B0 contract #2](https://github.com/Innovestro/aidumo-development-infrastructure/issues/2)
  and [B-first program #1](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1).
- [Suite architecture/audit #1731](https://github.com/Innovestro/aidumo-suite/issues/1731):
  [Target Model v4](https://github.com/Innovestro/aidumo-suite/issues/1731#issuecomment-5810054551),
  [fresh DEV Technical PASS](https://github.com/Innovestro/aidumo-suite/issues/1731#issuecomment-5810350363),
  and [Owner adoption and B-first sequencing](https://github.com/Innovestro/aidumo-suite/issues/1731#issuecomment-5810562319).

These links preserve authority; this repository does not copy the Suite governance
tree or redefine its contracts. Target architecture is not blanket implementation
permission. B must first adapt to **current A contracts** wherever possible.
Only a proven B capability and an evidenced, minimal integration gap justify
separately authorized, linked A-side work. B0 requires no Suite change.

## Repository and host placement

| Location | Contents |
| --- | --- |
| `README.md` | Purpose, authority, placement, security boundary and local setup. |
| [AGENTS.md](AGENTS.md) | Minimal CODEX/DEV contribution and review instructions. |
| [infrastructure/](infrastructure/README.md) | Future executable B source and non-secret configuration, added only by a concrete authorized capability. B1 CODEX runtime candidate under `infrastructure/codex-unraid/`. |
| Outside the checkout, in protected host-local storage | Credentials, worker sessions/workspaces, runtime journals, caches, logs, databases, persistent volumes and VM disks/snapshots. Never committed. |

Git may contain reviewed source, tests, reproducible definitions and non-secret
configuration examples required by an admitted B capability. It must not contain
live tokens, private keys, passwords, agent authentication/session material,
runner registration credentials, production credentials or actual host state.
Do not put these in `infrastructure/`, documentation, fixtures, PRs or check output.
Future runtime journals are recovery aids, not Suite authority; GitHub/A remains
the source of truth for Suite work.

[.gitignore](.gitignore) guards conventional local secret/state paths, including
`.env*`, `.secrets/`, `.local/`, `state/` and `runtime/`. These are accidental-file
guards, not recommended runtime locations or a complete secret detector. Keep
actual secrets and persistent state outside the checkout; inspect every staged
diff and never force-add them. Only sanitized examples may enter Git.

## Credential boundary for later capabilities

These are constraints for admitted capabilities; they were not provisioned by B0.
The [B1 runbook](infrastructure/codex-unraid/README.md) applies them to #4:

- **Coordinator:** read-only access for shadow work. No Product/scope/profile
  decisions; no writes or dispatch without explicit authority for that operation.
- **Executor:** access limited to its assigned package/workspace. No merge,
  release, production or repository-admin credentials in agent workspaces.
- **Runner:** isolated qualification environment, without broad agent, merge,
  release or production credentials. Do not mount shared host secrets or another
  system's credential store into jobs.
- **Publisher:** source publishing limited to the assigned branch/PR;
  evidence publishing limited to its authorized producer contract. Integration
  credentials remain separate. Possession of a token does not authorize an action.

Use separate, least-privilege credentials for each authorized role and inject
them from protected host-local storage only where needed. Do not share C's
browser-runner credentials with B. A future B/C integration may only request an
already-authorized run and consume its terminal result under C's contract.
Missing or ambiguous authority blocks the affected operation. No credentials,
host services or security-enforcement mechanisms are provisioned by B0.

## Start from a clean clone

Prerequisites: Git, a text editor and access to the repository and linked GitHub
contracts. GitHub CLI (`gh`) is optional for reading issues and opening the PR;
keep its authentication in the local credential store, outside the repository.

```sh
git clone https://github.com/Innovestro/aidumo-development-infrastructure.git
cd aidumo-development-infrastructure
git status --short --branch
```

Read this file, [AGENTS.md](AGENTS.md), the assigned issue including comments, and
its authoritative references before changing files. For the current B1 follow-up,
read #10 and current #1 Owner decisions; use the [Unraid runbook](infrastructure/codex-unraid/README.md) for its build, checks
and Owner setup. B0 #2 needed no dependencies or runtime. B1 needs no Suite or
External Tester checkout and introduces no CI workflow.

Work on an issue branch, inspect the complete diff and run `git diff --check`
(plus `git diff --cached --check` for staged changes). Confirm local Markdown
links resolve, cited authority references are correct, and conventional secret/
state paths are ignored using `git check-ignore`. Review a fresh clone of the
candidate to verify that it is self-contained. Record checks and their limits
in the canonical PR; these checks establish bootstrap integrity, not runtime
or Product qualification.

## B0 baseline and subsequent admission

B0 implemented none of the following: shadow coordinator, agent dispatch,
CODEX/Claude/Copilot adapters, Docker worker runtime, self-hosted runner,
Linux/FreeBSD VM lifecycle, GitHub publisher,
evidence reuse, scheduler/CODER replacement or production deployment automation.
No Suite policy/workflow or External Tester changes. No generic agent platform,
bootstrap generator, duplicate queue/state authority or speculative infrastructure.

B1 #4 separately admits one CODEX container, its bounded Git/GitHub access,
persistent state and actual restart/task proof. It does not admit the other
mechanisms above. Use a separate lineage from B0.

New mechanism classes default to **zero**: services/daemons, queues, repositories,
workflow/control-plane families, persistent state authorities, generic frameworks,
provider abstractions, compatibility/recovery/concurrency layers, extra security
mechanisms, evidence systems/producers and review/qualification gates. A concrete
current capability must need the mechanism **and** its authorized contract/budget
must permit it. A possible future consumer or an AI-written proposal is not
permission. Prefer the smallest sufficient change and stop when its contract is
satisfied. B0 ends with the documented technical review described in
[AGENTS.md](AGENTS.md); do not begin B1 in this lineage.

# Working in Development Infrastructure (B)

Read [README.md](README.md) for A/B/C authority, placement, credential boundaries
and the default-zero mechanism rule. These instructions apply to this repository;
they do not replace `aidumo-suite` governance.

1. Read the assigned GitHub issue, all its comments and authoritative references.
   Inspect repository status and existing branches/PRs before editing. Respect
   existing ownership and applicable claims/routing; do not create a parallel
   Suite claim or work queue here. Work only on the explicitly assigned package.
2. For B0, [#2](https://github.com/Innovestro/aidumo-development-infrastructure/issues/2)
   authorizes documentation/configuration bootstrap only. Use one issue branch
   and exactly one canonical PR. Reuse that PR for fixes. Do not start #3/B1 or
   other follow-up work, build future infrastructure, or change A/C repositories.
3. Make routine technical choices autonomously within the contract. Prefer
   existing conventions and the smallest coherent, reversible implementation.
   Fix in-scope defects. A candidate improvement is not an admitted task; missing
   human scope/budget authority blocks only the affected work, not unrelated work.
   Do not expand Product semantics, supported states, assurance or mechanisms.
4. Put future executable B source and non-secret configuration under
   `infrastructure/` only when required by an authorized capability. Keep real
   credentials and persistent host state outside the checkout. Review staged
   content for secrets; `.gitignore` alone is not a security boundary.
5. Run checks proportional to the actual change. For B0 use the README's local
   checks and inspect all #2 acceptance criteria against a clean clone. Do not
   introduce a test framework, CI workflow or governance tree to validate prose.
6. CODEX implements and self-checks; DEV independently performs Technical Review
   against the contract and exact candidate. The PR handoff must state the exact
   full head SHA, changed files with rationale, performed checks/results, scope
   exclusions and genuine remaining blockers. A self-check is not a DEV PASS.
   Keep GitHub issue/PR evidence canonical; no local readiness/review ledger.

For B0, stop after delivering the qualified canonical PR for **DEV Technical
Review**. Do not merge, grant Product acceptance, change repository settings or
activate infrastructure as part of that handoff.

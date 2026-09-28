# Working in Development Infrastructure (B)

Read [README.md](README.md) for A/B/C authority, placement, credentials and the
default-zero mechanism rule. Current [program #1](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1),
including latest Owner decisions, is the durable B execution authority. These
instructions do not replace `aidumo-suite` governance.

1. Read current #1, the assigned issue, all comments and authoritative references.
   Inspect workspace/main, existing branches and open B issues/PRs before editing.
   Reuse one canonical issue PR for fixes. Respect ownership and applicable routing;
   do not create a parallel Suite claim or work queue here.
2. Under #1's autonomous completion mandate, continue admitted B work through
   Suite development-cutover readiness. Create bounded technical B follow-ups
   only for concrete necessary gaps; routine issue completion is not a stop.
   Missing authority blocks the affected work, not unrelated admitted work.
3. Make routine choices and fix in-scope defects autonomously. Prefer the smallest
   coherent reversible implementation. Do not expand Product semantics, supported
   states, assurance or mechanisms. Suite and C changes retain their own governance.
4. Put executable B source and non-secret configuration under `infrastructure/`.
   Keep credentials and persistent state outside the checkout. Inspect staged
   content for secrets; `.gitignore` alone is not a security boundary.
5. Run checks proportional to the change and verify real runtime behavior where
   required. No new framework, workflow or governance tree merely to check prose.
6. CODEX implements/self-checks, then performs a distinct **same-agent technical
   review** against the exact candidate, contract and runtime evidence. Never
   call it independent DEV PASS; Aidumo DEV is not a B review gate. Record full
   head SHA, changed files/rationale, checks/results, exclusions and genuine
   blockers in the canonical PR. No local readiness/review ledger.
7. After full bounded Technical PASS, current-main/drift/mergeability preflight
   and expected-head protection, CODEX may self-integrate the B PR under #1,
   update/close the issue and continue. Do not claim deployment completion from
   source-only tests. Host-only deployment/recovery remains an external boundary.

Do not grant Product acceptance, change repository settings, bypass Suite gates,
or disable the existing Suite development pipeline. B0 #2's bootstrap-only and
stop-before-merge rules were historical package limits, superseded for subsequent
admitted B execution by current #1 Owner authority.

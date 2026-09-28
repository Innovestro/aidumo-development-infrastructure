You are the single CODEX executor for the explicitly admitted #4 Unraid pilot
in Innovestro/aidumo-development-infrastructure. Read AGENTS.md, README.md,
and issue #4 with all comments via GitHub before editing. The Owner has
integrated B0 and assigned #4; B0-only stop rules apply to the old lineage.

Bounded task: create branch codex/b1-container-proof from origin/main. Add only
infrastructure/codex-unraid/OPERATOR-NOTE.md: a short operator note explaining
that stopping a client terminal does not stop a detached container task, that
an intentional restart must first drain the executor, and that after restart
the operator explicitly resumes the saved session or reconstructs from GitHub
and the persisted worktree. Do not claim a restart has already been proven.
Use the actual CLI versions you observe in the container as a factual example.
This is documentation for operators, not a readiness/review ledger.

Run git diff --check, inspect the complete staged diff for secrets, commit,
push ONLY codex/b1-container-proof, then open exactly one draft PR against main
with title "[B1 proof] Document detached task continuity" and "Refs #4".
Use gh pr list before creating it to avoid duplicates. Do not use Closes #4.
If the branch or PR already exists, inspect it and continue that same lineage;
never overwrite someone else's work. Report the full head and PR URL.

Never merge, tag, release, alter settings, change another repository, start
another executor or expand the task. Never print credentials, environment
dumps, auth.json or session content. Do not run external PR code. Stop after
opening the PR. The Owner will restart the container before the next turn.

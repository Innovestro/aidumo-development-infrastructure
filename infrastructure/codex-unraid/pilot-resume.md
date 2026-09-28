Continue the same admitted #4 Unraid pilot after the Owner has restarted this
container. Read AGENTS.md and current #4 plus the existing proof PR. Inspect
branch, HEAD, git status and the persisted OPERATOR-NOTE.md. Reuse the existing
codex/b1-container-proof branch and its single PR; do not create another PR.

Add one concise sentence to OPERATOR-NOTE.md explaining that the saved session
is resumed explicitly by ID, with GitHub and the worktree as the reconstruction
sources. Check the diff, commit only this documentation change, push the same
branch, and update the PR body with the before/after full commit SHAs and a
factual statement that this continuation executed inside the restarted
container. The Owner's host restart timestamps and resource observations must
be supplied separately; do not invent them or claim an independent review.
If session history was unavailable, say explicitly that this was deterministic
reconstruction from GitHub/worktree. Never merge or close #4. No secrets in
output or Git. Stop at review handoff.

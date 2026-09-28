# B source publication and recovery (#17)

This CLI publishes one explicitly admitted **new B branch and its canonical PR**.
It does not authorize work or replace technical review/integration. Run from a
clean B checkout at the exact intended candidate, with normal standing B Git/PR
credentials. Keep the PR body outside the checkout and include `Closes #17`
(substitute the owning issue). Branch names are `codex/<issue>-<name>`.

```sh
python3 infrastructure/publisher/publish.py --issue 17 \
  --branch codex/17-publication-recovery --head FULL_CANDIDATE_SHA \
  --title 'Bounded publication recovery (#17)' --body-file /outside/pr-body.md
```

Git origin must be the existing B SSH transport. The CLI has no Suite writer,
merge, dispatch or settings path. It prints only result/PR identity, not captured
credential-bearing process diagnostics. Exit 2 means blocked, with no retry
permission. Run tests with `python3 -m unittest discover -s infrastructure/publisher`.

The branch/head and all-state GitHub PR evidence identify the publication. An
existing matching PR is returned unchanged, including after restart or branch
deletion; a closed PR is never replaced. Multiple PRs, changed heads, unrelated
PRs, API failure or incomplete inventories block. Only an invocation that
successfully creates an absent branch using an explicit absent-ref Git lease
may attempt PR creation, once. A failed/lost create response is reconciled by
reading GitHub; no blind retry occurs. A branch with no visible PR is unknown,
even if it might be a harmless interruption before creation. That conservative
stop is intentional. No local authoritative state, journal, queue or service is
needed. A lost push response leaves a branch-only outcome and also stops.

For blocked branch-only publication, inspect the exact remote branch, all-state
PRs and the failed command evidence in the existing issue. Do not delete/recreate
the branch, rename the operation, or repeatedly invoke raw PR creation to force
progress. Reconcile the actual remote outcome under the owning issue's authority;
only a separately justified recovery action can continue. This CLI does not
claim to fence arbitrary agent commands, malicious writers, or an operator who
deletes both remote identity carriers. Preserve those carriers while recovery
is unresolved. Ordinary later edits reuse the canonical PR with expected-head
Git publication and the owning repository's fresh claim/review rules.

## Controlled cutover and rollback boundary

B's shadow observer grants no execution or CI authority. Before moving a Suite
package to the persistent executor, Suite DEV must admit that exact execution
path/package and preserve canonical claim, head-bound qualification, technical
review and protected integration. Existing Suite work/PRs must be reconciled,
not copied to a second queue. This B-only publisher is not a Suite adapter.

Until those gates and complete Suite check visibility are satisfied, leave the
old pipeline enabled and the persistent executor drained between explicitly
admitted turns. No task is automatically resumed on container start. For a
controlled trial, finish/drain the current writer, inspect current Suite claims
and exact issue/PR/head/check state, and admit only the selected bounded package.

Rollback: drain the B executor and wait for its current turn to end. Read actual
GitHub outcomes before resuming the existing Suite lineage through its normal
claim/routing rules. Do not run old/new writers simultaneously, reopen terminal
claims, create a replacement PR or replay ambiguous side effects. Keep B
workspace/session state for diagnosis; it grants no claim authority. Since the
old pipeline has not been disabled, rollback currently requires no settings or
scheduler activation change. Any eventual old-pipeline retirement remains a
separate Suite/Owner gate after the replacement path is proven.

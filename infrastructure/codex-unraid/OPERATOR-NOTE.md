# Detached task continuity on Unraid

Once the pilot runtime has submitted a detached container task, closing or
stopping the client terminal does not stop that task. Execution continues in
the running Unraid container; reconnect to inspect its outcome and the GitHub
branch/PR before submitting more work.

Before an intentional container restart, drain the executor: block new tasks
and wait for the active task to finish. If draining times out, leave the
executor drained and wait; do not force a restart to interrupt the task.

After restart, the executor starts drained and does not automatically replay
work. The operator explicitly undrains and resumes the intended saved session
through the pilot runtime. If that session cannot be resumed, first inspect
the GitHub issue/PR and persisted worktree, then reconstruct the same bounded
task. Preserve existing changes and check for completed remote writes before
retrying; continue the same branch/PR.
Resume the saved session explicitly by ID, using GitHub and the persisted
worktree as the reconstruction sources if needed.

As a factual version example, this container reported `codex-cli 0.157.1`,
`gh version 2.101.0 (2026-09-15)`, and `git version 2.39.5` during preparation
of this note. These observations do not establish restart continuity: a
container restart and subsequent resume or reconstruction remain to be proven.

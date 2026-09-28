# One CODEX executor on Unraid — #4

This is the B1 runtime candidate for [#4](https://github.com/Innovestro/aidumo-development-infrastructure/issues/4),
not an acceptance claim. One linux/amd64 container, manually admitted tasks,
no dispatch/queue/other agents. Unraid is `192.168.40.10`; the Linux/FreeBSD VMs
are qualification targets and are not used here. No Suite or External Tester
changes. Bootstrap can happen on a laptop; a submitted task runs on Unraid even
when that laptop is off. Acceptance still requires the real pilot below.

## Layout and limits

- `Dockerfile`: digest-pinned Node/Debian base, CODEX CLI 0.157.1, Git, checksum-pinned GitHub CLI 2.101.0,
  SSH and Python. Debian security packages resolve at build time; save the image
  ID and installed versions. Rebuildable configuration is not bit-identical
  future apt output. Keep the qualified image until a replacement is qualified.
- `unraid.sh`: host-side build/create/start/drain/stop/restart/run/resume/logs/measure.
  No Compose plugin, host daemon, published port or Docker socket mount.
- `runtime.py`: one nonblocking execution lock, explicit admission, bounded
  metadata logs and numeric resource samples. Startup is always drained. A
  crash never automatically replays a task or remote write.
- `config.toml`: supported file auth, persisted sessions; Docker is the sandbox.
  CODEX has full access **inside** this single-purpose container. The container
  user is UID/GID 1000, root filesystem read-only, capabilities dropped,
  no-new-privileges, default Docker bridge/seccomp, no host networking/devices.
- Limits: 2 CPU, 4 GiB RAM with no extra swap, 256 PIDs, 256 MiB `/tmp`, 16 MiB
  ephemeral home. Workspace + CODEX + state admission ceiling 10 GiB, with at
  least 1 GiB free before a task. This is **not a hard filesystem quota**:
  monitor storage during tasks and drain before reaching the budget. Owner
  pool capacity remains a prerequisite; no new pool/VM is created.

| Host path under `/mnt/user/appdata/aidumo-codex` | Container | Access |
| --- | --- | --- |
| `workspace/` | `/workspace` | rw; only this B checkout and task files |
| `codex/` | `/codex` (`CODEX_HOME`) | rw; auth/config/session state, private |
| `state/` | `/state` | rw; lock, drain marker, prompt, session ID, exit code, metadata |
| `secrets/git_key` | `/run/secrets/git_key` | read-only dedicated Git key |
| `secrets/gh_token` | `/run/secrets/gh_token` | read-only dedicated PR token |

No NAS root, Owner home, host SSH directory, Unraid flash or other appdata is
mounted. Persistent data lives outside the configuration checkout. Do not share
this appdata over SMB/NFS; protect backups like credentials. Session transcripts
are private runtime state, not ordinary logs and never PR attachments. Container
removal retains bind-mounted data; never delete these directories to recreate.

## Owner step 1 — bootstrap on Unraid

The Owner deploys on the **live production Unraid host** using its web terminal.
CODEX does not receive SSH access or execute host setup. Do not use either VM.
Prerequisites: Docker running, outgoing HTTPS to OpenAI/GitHub/npm/Debian and SSH
port 22 to GitHub, space for image plus the 10 GiB data budget. Use the existing
appdata pool; do not create additional infrastructure. Commands assume Bash.

Download the reviewed PR's **exact full head** (provided in its handoff):

```bash
B1_HEAD=REPLACE_WITH_REVIEWED_FULL_HEAD
mkdir -p /mnt/user/appdata/aidumo-codex-source
cd /mnt/user/appdata/aidumo-codex-source
curl -fL "https://github.com/Innovestro/aidumo-development-infrastructure/archive/$B1_HEAD.tar.gz" -o source.tar.gz
tar -xzf source.tar.gz
cd "aidumo-development-infrastructure-$B1_HEAD/infrastructure/codex-unraid"
# Load the handoff image copied by the Owner (verify its supplied checksum first):
docker load -i /path/you/copied/aidumo-codex-b1.tar
# Alternative, only during an Owner-chosen build window: ./unraid.sh build
install -d -m 700 /mnt/user/appdata/aidumo-codex
for part in workspace codex state secrets; do
  install -d -m 700 -o 1000 -g 1000 "/mnt/user/appdata/aidumo-codex/$part"
done
```

The handoff may provide a locally built image archive and SHA-256 checksum.
Verify it with `sha256sum`, use `docker load -i`, then **skip build**. This avoids
image-build load on the production NAS. Build commands do not carry container
CPU/RAM limits. All smoke testing before this handoff runs on local Docker, not
on Unraid. Do not stop/restart Docker itself or unrelated containers.

Use a fresh dedicated directory. Do not recursively chown existing appdata.
`B1_ROOT` can select an equivalent private path on an existing pool;
`B1_CONTAINER`/`B1_IMAGE` are available for local smoke checks only. The pilot
uses the defaults. Do not run a second production executor.

## Owner step 2 — bound GitHub access before granting write credentials

A token with Contents:write also authorizes GitHub merge/release endpoints;
there is no separate PAT "push but never release" checkbox. Do **not** put an
Owner/classic/Contents-write token in this runtime.

Use two narrowly scoped credentials:

1. A fresh repository-only SSH deploy key for Git transport. It has no REST API
   bearer-token capability. Its default Git write scope is too broad, so first
   import `branches.ruleset.json` and `tags.ruleset.json` in this repository's
   **Settings → Rules → Rulesets → Import a ruleset**. Both must be **Active**,
   with **no bypass actors**, including no deploy-key or admin bypass. They
   block creation/update/deletion of all branches except
   `codex/b1-container-proof`, and all tags. This also blocks the Owner and
   bootstrap branch until the pilot ends; it is an explicit temporary Owner
   setup action, not an autonomous settings change. Keep other protections.
2. A fine-grained PAT for **only** this repository, **Pull requests: read/write**,
   **Contents: read-only**, **Issues: read-only** (contract/comments), implicit
   Metadata:read, no other permissions, short
   expiry (e.g. seven days). It cannot perform the Contents-write merge/release
   API operations. The token's identity still needs access to this repository;
   organization approval may be required. It is used only by gh/API calls.

In the Unraid terminal, generate the Git key (no passphrase for this dedicated,
protected, noninteractive key):

```bash
ssh-keygen -t ed25519 -N '' -C aidumo-codex-b1 -f /mnt/user/appdata/aidumo-codex/secrets/git_key
cat /mnt/user/appdata/aidumo-codex/secrets/git_key.pub
```

Register **only the public key** in this repository's Settings → Deploy keys,
with write access. Never add it to the bypass list. Enter the fine-grained PAT
without shell history or echo:

```bash
read -rsp 'B1 PR-only token: ' b1_token; echo
(umask 077; printf '%s' "$b1_token" > /mnt/user/appdata/aidumo-codex/secrets/gh_token)
unset b1_token
chown 1000:1000 /mnt/user/appdata/aidumo-codex/secrets/git_key /mnt/user/appdata/aidumo-codex/secrets/gh_token
chmod 600 /mnt/user/appdata/aidumo-codex/secrets/git_key /mnt/user/appdata/aidumo-codex/secrets/gh_token
./unraid.sh create
```

The public host key is pinned from GitHub's HTTPS `/meta` endpoint. Never disable
SSH host verification; investigate a mismatch against GitHub's official keys.
No app/private-key issuer, proxy or custom authentication service is introduced.

## Owner step 3 — supported CODEX authentication

Default for detached execution: a dedicated OpenAI project API key, entered
through stdin and persisted by CODEX itself in `/codex/auth.json`. Set the
project budget/usage alerts in OpenAI; billing is separate from a ChatGPT
subscription. No API calls or spending are triggered by the image build.

```bash
read -rsp 'Dedicated OpenAI API key: ' b1_openai_key; echo
printf '%s' "$b1_openai_key" | ./unraid.sh login-api
unset b1_openai_key
./unraid.sh auth-status
```

Official CLI also supports `./unraid.sh login` (device-code ChatGPT login,
if enabled for the account/workspace) and file-backed refresh. This public
repository pilot does **not** prescribe copying a laptop auth cache into an
unattended CI workflow: OpenAI's advanced account-auth CI guidance excludes
public repositories. Use the API-key path for the detached pilot. Never mount
the laptop's whole `.codex` directory, plugin connectors or credential stores.
If the supported login is unavailable or cannot persist securely, **stop the
affected pilot**, report the actual error without secrets, and do not build an
auth workaround. A browser may be needed for initial account setup only.

## Owner step 4 — prepare and verify the bounded workspace

Enter `./unraid.sh shell` and execute inside the container:

```bash
git clone git@github.com:Innovestro/aidumo-development-infrastructure.git /workspace/aidumo-development-infrastructure
cd /workspace/aidumo-development-infrastructure
git config user.name 'CODEX Unraid pilot'
git config user.email 'codex-unraid@users.noreply.github.com'
codex --version
git --version
gh --version
```

Exit the container shell. Before the first task the Owner must verify both
active rulesets in GitHub, zero bypass actors, exact branch exclusion, and the
PAT permission page. Record sanitized settings/credential type/expiry evidence
in the canonical #4 PR; never token/key values. Existing repository settings
were unprotected at bootstrap inspection, so this is a real prerequisite.
Ruleset imports are **not** part of `create` and must not be skipped.

## Real pilot and restart proof

The two supplied prompts are the deliberately small admitted B documentation
task required by #4; they do not authorize other work. The bootstrap PR and
this proof PR are separate, both within #4. The proof starts from current main.
Never reuse B0 PR #7. PR evidence remains canonical; no local readiness ledger.

On Unraid, from this configuration directory:

```bash
./unraid.sh undrain
./unraid.sh run pilot-task.md
./unraid.sh logs
./unraid.sh measure
```

`run` submits a detached `docker exec`; submission alone is **not** task success.
A second active run is refused (exit 75), never queued. Check the metadata
`started`/`finished` events and `/state/exit-code`; CODEX exit 0 alone does not
prove acceptance either. Verify the actual proof branch, commit and PR on
GitHub. A login/rate-limit/network error is an incomplete run; no blind retry
of remote writes. Ordinary output intentionally omits model/tool/error text.
For diagnosis inspect protected CODEX state locally; do not publish transcripts.

Close the Owner laptop/client while the task executes. Reconnect later through
Unraid and record start/end UTC timestamps, proof head and PR URL. Snapshot:

```bash
docker inspect aidumo-codex --format 'ID={{.Id}} Image={{.Image}} Started={{.State.StartedAt}} OOM={{.State.OOMKilled}}'
./unraid.sh measure
docker exec aidumo-codex sh -c 'cat /state/session-id; cat /state/exit-code; git -C /workspace/aidumo-development-infrastructure rev-parse HEAD; git -C /workspace/aidumo-development-infrastructure status --short'
./unraid.sh restart
./unraid.sh auth-status
docker inspect aidumo-codex --format 'ID={{.Id}} Image={{.Image}} Started={{.State.StartedAt}} OOM={{.State.OOMKilled}}'
docker exec aidumo-codex sh -c 'cat /state/session-id; git -C /workspace/aidumo-development-infrastructure rev-parse HEAD; git -C /workspace/aidumo-development-infrastructure status --short'
./unraid.sh undrain
./unraid.sh resume pilot-resume.md
```

After it finishes, verify a second commit on the **same** proof branch/PR and
collect `logs`/`measure` again. The session ID is selected explicitly, never
`--last`. If the supported resume cannot load the session, inspect the worktree
and PR first, then `run pilot-resume.md` reconstructs the task deterministically;
report reconstruction rather than a successful session resume. Never reset or
reclone a dirty worktree to hide missing state.

Acceptance evidence must contain the exact bootstrap/proof heads and image ID,
Unraid identity, observed versions, successful branch/edit/commit/push/PR,
before/after container StartedAt, unchanged workspace head/status/session ID at
restart, valid auth without secret values, continuation commit, laptop-off
interval, mount/security/credential checks, and measured resources. Runtime
metadata samples cgroup v2 CPU microseconds, RAM bytes and PIDs every five
seconds; CPU deltas over elapsed time give actual CPU consumption. `measure`
adds Docker CPU/RAM/network/block I/O, image bytes and per-volume storage bytes.
On cgroup v1, collect Docker stats during the run; missing samples are not zero
usage. Logs rotate at 1 MiB plus one backup. Private CODEX state counts toward
the storage budget and is never automatically deleted.

## Operations and recovery

- `drain`: blocks new tasks, waits up to 60 seconds for the executor. A timeout
  leaves it drained and running; retry after the task finishes. It never kills
  a task merely to make a restart test pass.
- `stop` / `restart`: drain first. `start` or automatic host-reboot restart
  returns an idle, drained container. Explicit `undrain` and run/resume required.
- Unexpected loss/OOM: inspect Git/GitHub before resuming, since remote writes
  may have completed. State is recovery context, not authority. There is no
  exactly-once guarantee or automatic retry/reconciliation service.
- `shell`: operator diagnosis only. Do not start a second CODEX directly around
  the executor lock. GitHub tools in this shell do not automatically receive
  the PR token; the task invocation injects it.
- Recreation: drain/stop, save the qualified image ID, remove only the stopped
  container, then `create` using the same five mounts and image. Never use a
  volume-delete command. Reauthenticate only if auth actually expired/revoked.
- Rollback on Unraid: `./unraid.sh stop`, then
  `docker rm aidumo-codex` removes only this stopped container. Retain its private
  data for diagnosis; no host Docker restart, volume pruning or NAS changes.
  Revoke this pilot's deploy key/PAT (and OpenAI key if abandoning the pilot).
- End pilot: drain/stop, revoke the deploy key and PAT, then Owner can remove or
  revise the temporary rulesets to integrate reviewed PRs. For normal later
  work, explicitly admit a new B package/branch and adjust the existing branch
  exclusion before restoring bounded credentials. This is manual admission,
  not an automatically discovered work queue.

Remaining gates: Owner host/credential setup, real Unraid acceptance run and
applicable DEV/Owner review. Local smoke tests are not Unraid or model evidence;
the B0 same-agent review exception does not waive B1 review.

Sources: [OpenAI authentication](https://learn.chatgpt.com/docs/auth),
[noninteractive execution/resume](https://learn.chatgpt.com/docs/non-interactive-mode),
[GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository),
[merge permissions](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request),
[release permissions](https://docs.github.com/en/rest/releases/releases#create-a-release),
[deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys).

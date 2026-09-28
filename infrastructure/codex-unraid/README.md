# One CODEX executor on Unraid — #4

B1 [#4](https://github.com/Innovestro/aidumo-development-infrastructure/issues/4)
is integrated at `733197b8619a1b5d731131383ac0eade70e3c566`. This runbook adopts
standing GitHub access under [#10](https://github.com/Innovestro/aidumo-development-infrastructure/issues/10)
and the current Owner decisions in [#1](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1).
One linux/amd64 container executes manually admitted tasks; no dispatch, queue
or other agents. Unraid is `192.168.40.10`. The #5 access implementation adds only
bounded Linux guest SSH; Owner-operated VM reset is documented in the
[Linux VM runbook](../linux-vm/README.md). Suite qualification remains unbound.
A submitted task runs on Unraid even when the Owner laptop is off.

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
| `workspace/` | `/workspace` | rw; explicitly admitted checkouts and task files |
| `codex/` | `/codex` (`CODEX_HOME`) | rw; auth/config/session state, private |
| `state/` | `/state` | rw; lock, drain marker, prompt, session ID, exit code, metadata |
| `secrets/git_key` | `/run/secrets/git_key` | read-only standing B deploy key |
| `secrets/git_key_suite` | `/run/secrets/git_key_suite` | read-only standing Suite deploy key |
| `secrets/gh_token` | `/run/secrets/gh_token` | read-only standing PR/issue token |
| `secrets/linux_vm_key` | `/run/secrets/linux_vm_key` | read-only dedicated Linux guest key |
| `secrets/linux_vm_known_hosts` | `/run/secrets/linux_vm_known_hosts` | read-only Owner-pinned Linux host key |
| `secrets/freebsd_vm_key` | `/run/secrets/freebsd_vm_key` | read-only dedicated FreeBSD guest key |
| `secrets/freebsd_vm_known_hosts` | `/run/secrets/freebsd_vm_known_hosts` | read-only Owner-pinned FreeBSD host key |

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
`B1_CONTAINER` selects the container name for local smoke checks; production
uses the default. `B1_IMAGE` selects a reviewed image for build/create. Do not run a second production executor.

## Owner step 2 — standing GitHub access

The intended standing work set is `Innovestro/aidumo-development-infrastructure`
and `Innovestro/aidumo-suite`. The installed fine-grained PAT is intentionally
**not repository-restricted** by Owner decision. Credential reach is not work
authorization: every task still requires explicit repository/package admission
and compliance with that repository's governance. In Suite this includes claims,
role routing, Product/DEV/PM review, branch protections, required checks and
Owner-only integration. Additional repository work requires explicit authority.

The protected host secrets are already provisioned:

- `secrets/git_key`: standing write deploy key for this B repository; normal
  `github.com` Git identity.
- `secrets/git_key_suite`: separate standing write deploy key for Suite; selected
  only through `github-suite`, which connects to `github.com` with that key.
- `secrets/gh_token`: standing fine-grained PAT with Pull requests and Issues
  **read/write**, Contents and Metadata **read-only**, no other permissions.
  No admin/settings/secrets/releases/packages/Actions authority is granted.

Do not read, print or copy secret values into Git, prompts or logs. The Owner
maintains files owned by UID/GID 1000 with mode 600 under the private secrets
directory. `create` requires these three files plus the two Linux and two FreeBSD guest files
described below and mounts them individually
read-only. Retain the existing credentials between normal admitted packages;
rotate for expiry, compromise or an Owner-directed access change, not per task.
No new rulesets or changes to existing protections are required by #10. The
retired `branches.ruleset.json` and `tags.ruleset.json` are historical B1 pilot
artifacts, not standing setup instructions; do not import them.

SSH remotes must select the matching repository key:

```text
git@github.com:Innovestro/aidumo-development-infrastructure.git
git@github-suite:Innovestro/aidumo-suite.git
```

For an already admitted Suite checkout, set its origin to the second URL before
Git operations. #10 does not authorize Suite edits or a Suite proof branch.
Both hosts use only their configured key, disable the SSH agent and verify the
same pinned GitHub host key. Never disable host verification. The PAT is used
by gh/API calls, never as the Git push identity. Git write capability is not a
technical branch allowlist: task scope and existing repository protections
still apply. No merge, release, settings mutation or automatic integration is
authorized. Contents-write API permission must remain absent; Owner checks the
PAT permission page without publishing the token.

For fresh setup after provisioning, run `./unraid.sh create`. For the existing
container, use the current #6 recreation procedure below to retain workspace/auth/state.

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

Exit the container shell. The Owner verifies credential type, repository key
mapping and PAT functional permissions in GitHub. Record only sanitized evidence
in the canonical PR. Normal packages need admission, not credential recreation.
The runtime initially starts in the B checkout; a Suite task must explicitly
select its admitted checkout and read Suite governance before working there.

## Historical B1 pilot and restart proof

B1 is complete; PR #8 is integrated and proof PR #9 is closed unmerged. The
following procedure and supplied prompts document that original proof. Do not
rerun them for #10 or restore the retired pilot credentials/rulesets.

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
  container, then `create` using the reviewed mounts and image. Never use a
  volume-delete command. Reauthenticate only if auth actually expired/revoked.
- Rollback on Unraid: `./unraid.sh stop`, then
  `docker rm aidumo-codex` removes only this stopped container. Retain its private
  data for diagnosis; no host Docker restart, volume pruning or NAS changes.
  Retain standing GitHub credentials and OpenAI/CODEX auth/session state for
  subsequent admitted work unless the Owner directs revocation.
- Normal package completion: stop work at the package's review/integration gate.
  A later package needs explicit admission; no per-package key/PAT recreation,
  revocation or temporary branch ruleset is required.

## Historical #10 Owner deployment gate — completed

For current recreation use the #6 procedure below. This section records the
previous deployment using #10 source, which did not require Linux guest files.

The old running container lacks the Suite key mount and alias. Static checks
and B branch/API proof cannot establish real Suite Git transport. After the
candidate PR is self-checked and reviewed, the Owner runs the following in the
Unraid web terminal, after this task has finished. Use the exact full head from
the PR handoff. This changes only this container, retaining all persistent data.

```bash
(
set -e
B10_HEAD=REPLACE_WITH_REVIEWED_FULL_HEAD
mkdir -p /mnt/user/appdata/aidumo-codex-source
cd /mnt/user/appdata/aidumo-codex-source
curl -fL "https://github.com/Innovestro/aidumo-development-infrastructure/archive/$B10_HEAD.tar.gz" -o "$B10_HEAD.tar.gz"
tar -xzf "$B10_HEAD.tar.gz"
cd "aidumo-development-infrastructure-$B10_HEAD/infrastructure/codex-unraid"
# Check presence/permissions without reading secrets.
for secret in git_key git_key_suite gh_token; do
  test -s "/mnt/user/appdata/aidumo-codex/secrets/$secret" || exit 1
  chown 1000:1000 "/mnt/user/appdata/aidumo-codex/secrets/$secret"
  chmod 600 "/mnt/user/appdata/aidumo-codex/secrets/$secret"
done
# Reuse the installed image; only ssh.conf changes inside the image for #10.
B10_BASE=$(docker inspect aidumo-codex --format '{{.Image}}')
docker tag "$B10_BASE" aidumo-codex:pre-10
export B1_IMAGE="aidumo-codex:10-$B10_HEAD"
docker build --pull=false --build-arg BASE=aidumo-codex:pre-10 -t "$B1_IMAGE" -f - . <<'DOCKERFILE'
ARG BASE
FROM ${BASE}
COPY ssh.conf /etc/codex-ssh.conf
DOCKERFILE
# A failed drain must stop this sequence; never force-remove a running task.
./unraid.sh stop
docker rm aidumo-codex
./unraid.sh create
./unraid.sh auth-status
)
```

Keep the candidate image tag for future recreation (`B1_IMAGE` must select it).
The derived image avoids reinstalling packages on the production NAS; the normal
Dockerfile also includes the new SSH config on future full builds. The old image
is retained as `aidumo-codex:pre-10` for rollback using the old source/create
script and existing persistent data.

Leave the recreated runtime drained. Owner can then perform read-only transport
proof from that container (no Suite checkout or write is needed):

```bash
docker exec aidumo-codex git ls-remote git@github.com:Innovestro/aidumo-development-infrastructure.git HEAD
docker exec aidumo-codex git ls-remote git@github-suite:Innovestro/aidumo-suite.git HEAD
```

Record both results and the new image/container identity in the #10 canonical
PR; a successful read establishes transport, not Suite branch write permission
or authority to work. Owner verification of installed PAT permissions remains
necessary; API success alone cannot prove absence of Contents-write. No merge
or issue closure is part of this deployment proof.

For B, CODEX performs implementation/self-check and a distinct **same-agent
technical review** against the exact candidate and evidence. Aidumo DEV does not
work in this repository; this is never an independent DEV PASS. Following the
remaining deployment/transport proof and review, integration belongs to Owner.

Sources: [OpenAI authentication](https://learn.chatgpt.com/docs/auth),
[noninteractive execution/resume](https://learn.chatgpt.com/docs/non-interactive-mode),
[GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository),
[merge permissions](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request),
[release permissions](https://docs.github.com/en/rest/releases/releases#create-a-release),
[deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys).

## #5 first stage — bounded Linux guest SSH

[#5](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5)
consumes the existing `aidumo-linux-runner-01`: Owner-reported Ubuntu Server
26.04.1 LTS, kernel `7.0.0-34-generic`, UID/GID 1000 `aidumo` in `sudo`.
It remains a DHCP client reserved at `192.168.40.130`. This stage installs no
packages, runner or toolchain and performs no VM lifecycle/reset operations.
Guest sudo membership is existing guest authority, not Unraid host authority.
No Unraid root credentials, Docker/libvirt socket/API or broad NAS mount is added.

Inside the recreated CODEX container, use exactly:

```bash
ssh -F /etc/codex-ssh.conf aidumo@192.168.40.130 'hostname; id; uname -r'
```

The alias `aidumo-linux-runner-01` selects the same endpoint. Always supply `-F`:
`GIT_SSH_COMMAND` applies to Git, not ordinary SSH. The guest entry selects only
`/run/secrets/linux_vm_key`, disables agent and password fallback and forwarding,
and requires ED25519 verification against only the protected guest known-hosts
file. No first-use acceptance, `ssh-keyscan` trust or host-key update is used.
A missing key, unknown/changed host key or unavailable guest must fail; do not
weaken verification. The pinned file must contain the `192.168.40.130` entry
whose fingerprint is `SHA256:8fAqS7Pezv1AqJXyYMxievFCxa/l3TQSzlhOT8fDsxg`.
The Owner verifies this public fingerprint without reading private-key material.

### Historical Owner recreation gate — completed

Owner recreation and real container-to-guest transport were recorded in PR #12
on 2026-09-28. No further container recreation is required for the final documentation update.
Continue with the [Linux VM characterization/reset runbook](../linux-vm/README.md).
The following retains the original recreation procedure for future Owner use,
substituting the reviewed full head after the active task finishes.
The three persistent bind directories and existing GitHub credentials are reused.
The small derived image copies only SSH configuration from this candidate.

```bash
(
set -e
B5_HEAD=REPLACE_WITH_REVIEWED_FULL_HEAD
mkdir -p /mnt/user/appdata/aidumo-codex-source
cd /mnt/user/appdata/aidumo-codex-source
curl -fL "https://github.com/Innovestro/aidumo-development-infrastructure/archive/$B5_HEAD.tar.gz" -o "$B5_HEAD.tar.gz"
tar -xzf "$B5_HEAD.tar.gz"
cd "aidumo-development-infrastructure-$B5_HEAD/infrastructure/codex-unraid"
# Presence/permissions only: never read or print the private key.
for secret in linux_vm_key linux_vm_known_hosts; do
  test -f "/mnt/user/appdata/aidumo-codex/secrets/$secret"
  test -s "/mnt/user/appdata/aidumo-codex/secrets/$secret"
  chown 1000:1000 "/mnt/user/appdata/aidumo-codex/secrets/$secret"
  chmod 600 "/mnt/user/appdata/aidumo-codex/secrets/$secret"
done
# Check only the public pinned host entry; abort on missing/multiple/wrong keys.
B5_PIN=$(ssh-keygen -F 192.168.40.130 -f /mnt/user/appdata/aidumo-codex/secrets/linux_vm_known_hosts | ssh-keygen -lf - -E sha256)
test "$(printf '%s\n' "$B5_PIN" | awk '{print $2, $NF}')" = 'SHA256:8fAqS7Pezv1AqJXyYMxievFCxa/l3TQSzlhOT8fDsxg (ED25519)'
B5_BASE=$(docker inspect aidumo-codex --format '{{.Image}}')
docker tag "$B5_BASE" aidumo-codex:pre-5
export B1_IMAGE="aidumo-codex:5-$B5_HEAD"
docker build --pull=false --build-arg BASE=aidumo-codex:pre-5 -t "$B1_IMAGE" -f - . <<'DOCKERFILE'
ARG BASE
FROM ${BASE}
COPY ssh.conf /etc/codex-ssh.conf
DOCKERFILE
# Failed drain stops here. Never force-remove a running task.
./unraid.sh stop
docker rm aidumo-codex
./unraid.sh create
./unraid.sh auth-status
)
```

Leave it drained. Keep `B1_IMAGE=aidumo-codex:5-<reviewed-full-head>` for future
recreation. No volume deletion, re-clone or reauthentication is required.
Rollback uses `aidumo-codex:pre-5` and the integrated #10 `unraid.sh` at
`5fd52760c0c5cb0030333f5fdab4d7246f360f44`, with the same persistent directories.

After recreation, the Owner can verify read-only guest transport:

```bash
docker exec aidumo-codex ssh -F /etc/codex-ssh.conf aidumo@192.168.40.130 'hostname; id; uname -r'
```

Record the result and new container/image identity in the single #5 PR. This
proves transport only. The completed Owner-operated dirty/reset/clean proof,
resource measurements and reset procedure are in the
[Linux VM runbook](../linux-vm/README.md). Integration remains Owner-only;
no Suite changes or GitHub Runner implementation are included.


## #6 first stage — bounded FreeBSD guest SSH

[#6](https://github.com/Innovestro/aidumo-development-infrastructure/issues/6)
consumes the real `aidumo-freebsd-hostpoint-01`, a DHCP client reserved at
`192.168.40.150`. Owner-verified baseline: FreeBSD 15.1-RELEASE (kernel/running/
userland), GENERIC amd64; user `aidumo`, UID/GID 1001:1001, groups `wheel` and
`aidumo`. These are Owner observations, not yet container-to-guest proof.
Guest wheel membership does not grant Unraid host authority.

Inside the recreated CODEX container, use exactly:

```bash
ssh -F /etc/codex-ssh.conf aidumo@192.168.40.150 'hostname; id; freebsd-version -kru; uname -m'
```

The alias `aidumo-freebsd-hostpoint-01` selects the same endpoint. Always supply
`-F`; ordinary SSH does not consume `GIT_SSH_COMMAND`. This entry uses only
`/run/secrets/freebsd_vm_key`, no agent/password fallback or forwarding, and
strict ED25519 verification using only `/run/secrets/freebsd_vm_known_hosts`.
Unknown/changed keys or missing credentials must fail; never accept first use
or weaken verification. The protected pin must contain `192.168.40.150` with
fingerprint `SHA256:/Q0hmFgAh20TdZtaKXqopF6e7615rLiN5+t4htFI41Y`, independently
verified by Owner against the authenticated guest host public key in #6.
Existing B/Suite/Linux SSH entries and credentials remain unchanged.

### Owner recreation gate — pending

Stop here until Owner recreates the existing persistent container after the
active task finishes. Run the following in the Unraid Bash terminal, using the
reviewed full head from the canonical #6 PR. It reuses the existing image with
only the candidate SSH configuration replaced, and all three existing persistent
bind directories (workspace, CODEX auth/sessions, runtime state). No re-clone,
volume deletion or reauthentication is needed. Host secret files must be readable
by container UID 1000, independently of guest UID 1001.

```bash
(
set -euo pipefail
B6_HEAD=REPLACE_WITH_REVIEWED_FULL_HEAD
export B1_ROOT=/mnt/user/appdata/aidumo-codex B1_CONTAINER=aidumo-codex
mkdir -p /mnt/user/appdata/aidumo-codex-source
cd /mnt/user/appdata/aidumo-codex-source
curl -fL "https://github.com/Innovestro/aidumo-development-infrastructure/archive/$B6_HEAD.tar.gz" -o "$B6_HEAD.tar.gz"
tar -xzf "$B6_HEAD.tar.gz"
cd "aidumo-development-infrastructure-$B6_HEAD/infrastructure/codex-unraid"
# Presence/permissions only; never print private-key material.
for secret in freebsd_vm_key freebsd_vm_known_hosts; do
  test -f "$B1_ROOT/secrets/$secret"
  test -s "$B1_ROOT/secrets/$secret"
  chown 1000:1000 "$B1_ROOT/secrets/$secret"
  chmod 600 "$B1_ROOT/secrets/$secret"
done
# Require exactly the independently verified public ED25519 pin.
B6_PIN=$(ssh-keygen -F 192.168.40.150 -f "$B1_ROOT/secrets/freebsd_vm_known_hosts" | ssh-keygen -lf - -E sha256)
test "$(printf '%s\n' "$B6_PIN" | awk '{print $2, $NF}')" = 'SHA256:/Q0hmFgAh20TdZtaKXqopF6e7615rLiN5+t4htFI41Y (ED25519)'
# Check existing credentials before stopping the container.
for secret in git_key git_key_suite gh_token linux_vm_key linux_vm_known_hosts; do
  test -f "$B1_ROOT/secrets/$secret"
  test -s "$B1_ROOT/secrets/$secret"
done
B6_BASE=$(docker inspect aidumo-codex --format '{{.Image}}')
docker tag "$B6_BASE" aidumo-codex:pre-6
export B1_IMAGE="aidumo-codex:6-$B6_HEAD"
docker build --pull=false --build-arg BASE=aidumo-codex:pre-6 -t "$B1_IMAGE" -f - . <<'DOCKERFILE'
ARG BASE
FROM ${BASE}
COPY ssh.conf /etc/codex-ssh.conf
DOCKERFILE
# A failed drain aborts before removal. Never force-remove an active task.
./unraid.sh stop
docker rm aidumo-codex
./unraid.sh create
./unraid.sh auth-status
)
```

Leave the container drained. Retain `B1_IMAGE=aidumo-codex:6-<reviewed-full-head>`
for subsequent recreation. Rollback uses `aidumo-codex:pre-6` and the integrated
`unraid.sh` at `610a706f82a3fa24d6e0a042b50e9cad122e2264`, with the same bind
directories and the same drain/stop/remove/create sequence. Do not delete state.

After recreation, the Owner can verify guest transport without installing anything:

```bash
docker exec aidumo-codex ssh -F /etc/codex-ssh.conf aidumo@192.168.40.150 'hostname; id; freebsd-version -kru; uname -m'
```

Record sanitized transport results and container/image identity in the canonical
#6 PR. Container-to-FreeBSD SSH remains unproven until that gate is completed.
This stage installs no packages and performs no PHP/web/DB setup, VM lifecycle,
reset, Suite/C changes or generalized provider orchestration. It adds no Unraid
root credentials, Docker/libvirt socket/API, broad NAS mount or production/
Hostpoint credentials. Local FreeBSD access does not establish Hostpoint
equivalence or complete #6 acceptance. Do not merge or close #6 at this handoff.

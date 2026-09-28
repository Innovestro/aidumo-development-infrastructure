# FreeBSD #6 local runtime profile

This is a synthetic local substrate characterization, **not Hostpoint equivalence**
and not qualification of an Aidumo application revision. Exact candidate, review
and execution evidence live in [PR #13](https://github.com/Innovestro/aidumo-development-infrastructure/pull/13)
and [#6](https://github.com/Innovestro/aidumo-development-infrastructure/issues/6).
The [package authority](runtime-preparation.md#authority-derived-package-set)
consumes Suite deployment requirements at `dcdea09ffd16cb20485d369772aac018451483de`
without changing Suite or its existing qualification/deployment gates.

## Access and installed state

On 2026-09-28, persistent CODEX verified strict pinned root SSH: uid 0,
hostname `aidumo-freebsd-hostpoint-01`, installed/running kernel and userland
all `15.1-RELEASE`. Effective root sshd policy requires publickey, prohibits
password/keyboard-interactive, forwarding, PTY and user-rc. Existing non-root
`aidumo` SSH remains available. Root password stays Owner-only. This grants no
Unraid, libvirt/Docker socket, other-VM, NAS or Hostpoint authority.

Before installation: pkg/pkg-static 2.7.5, inventory only `pkg-2.7.5`, no runtime
listeners, clean zroot. Staged resume SHA256 matched
`45f9d7a841ee89910e6bdffa8a12f4cd6b4027e01b61a96939069cb38c5a3b30`; both guarded
catalogue hashes matched. CODEX copied it to root-owned storage, verified its
hash again and ran it. Corrected dry-run, full fetch, install and capability
checks all succeeded, using retained metadata without re-bootstrap/update.

Installed: 22 direct packages plus 33 resolver dependencies, 56 inventory entries
including pkg. PHP/extension packages 8.3.33, Composer 2.10.3, Apache 2.4.68,
MariaDB client/server 11.4.13. No Node/npm, nginx, Git or broad development
package set was requested. Dependencies include MariaDB's galera/rsync/Perl and
client libraries; their presence does not authorize clustering or extra services.
FreeBSD base compiler tools predate this installation. Binary patch versions and
catalogue availability are observations, not a perpetual reproducibility promise.

## Smallest deliberate profile

Non-secret source is in [profile/](profile/). It uses package rc services, with no
new daemon, orchestration layer, CI workflow or test framework:

- Apache event MPM, `www`, loopback `127.0.0.1:18080` / `:18443`; no mod_php.
  `proxy_fcgi` connects to FPM over `/var/run/b6-fpm.sock` (`www:www` 0600).
- FPM pool runs as dedicated `b6web:b6web` (observed uid/gid 1002), no login shell.
  Public code is root-owned 0755/0644 in `/usr/local/www/aidumo-b6/public`.
  Private `/var/db/aidumo-b6/private` is b6web-owned 0700; fixture files 0600.
  FPM rc umask is 0077. No source-tree-wide writable permissions.
- MariaDB runs as `mysql`, TCP bound only to 127.0.0.1:3306 plus its local socket.
  Default anonymous accounts and `test` database were removed. `b6web@localhost`
  authenticates by OS identity (`unix_socket`), with all privileges only on
  `b6_fixture.*` and SELECT only on `b6_persistence.*`; no global privileges.
  This intentionally proves local PDO socket use, not provider password/remote TLS.
- TLS uses a dedicated 30-day self-signed server certificate for localhost and
  127.0.0.1, CA:FALSE/serverAuth. Private key is root-only outside Git. Probes trust
  the exact certificate; normal trust rejects it (curl exit 60). No `-k` bypass.
  Final observed SHA256 fingerprint:
  `2A:06:8A:1A:25:91:F4:70:4D:C8:37:82:40:82:21:AC:84:42:3E:D4:1D:08:8F:11:8A:9A:C7:2E:80:78:35:A8`.
  Valid 2026-09-28 18:45:54 UTC through 2026-10-28 18:45:54 UTC. Regeneration
  requires reloading Apache and trusting the newly inspected exact certificate.

## Measured execution

[verify.sh](profile/verify.sh) passed real CLI and HTTP/HTTPS probes. Both protocols
returned PHP 8.3.33 / `fpm-fcgi`, no missing required extensions, correct public
DocumentRoot, writable private path, non-writable public code, and the persistent
DB marker through ordinary-user PDO. Composer ran as b6web, never root. This is
Composer/PHAR availability, not Suite dependency installation or platform-check PASS.

Real `.htaccess` maps `/rewritten` to `index.php`; the response retains the original
URI. Missing paths return 404. `/.htaccess` and `/.env` return 403; `/fixture.php`
and `/private/persistence` return 404. `X-Content-Type-Options: nosniff` is present,
`X-Powered-By` absent, and an incoming `Proxy` header is removed. HTTPS reaches
FPM with HTTPS=on. No assertion about Hostpoint proxy headers/topology follows.

[fixture.php](profile/fixture.php), as b6web, proved separate `Case`/`case` files,
same-directory rename and replacement, 0600 files, exclusive flock contention
between independent handles and another PHP process, release/reacquisition, and
cleanup. These are bounded ZFS/PHP examples, not proof of every crash, NFS,
Unicode, cross-dataset rename or concurrent application condition. Dataset:
`zroot/ROOT/default`, case-sensitive, normalization none, quota none, compression
on. Public/private ownership and mode checks agree with actual FPM behavior.

Ordinary-user PDO created `b6_fixture`, created a table, inserted/updated/read its
row, dropped the table/database and verified absence. Access to `mysql.user` was
denied. A separately provisioned read-only DB marker and private file are retained
for restart checks; no production data or provider credentials are used.

## Limits: observed defaults versus local choices

No php.ini is loaded; package extension ini files are loaded. CLI observations
are under the dedicated fixture identity. FPM values below come from HTTP JSON;
`php-fpm -i` alone reports binary defaults, not pool overrides.

| Setting | CLI / binary default observed | Configured FPM request |
| --- | --- | --- |
| memory_limit | 128M | 128M |
| max_execution_time | CLI 0; FPM binary default 30 | 5 seconds |
| max_input_time | -1 | 30 seconds |
| upload_max_filesize / post_max_size | 2M / 8M | 2M / 8M |
| max_input_vars | 1000 | 1000 |
| default_socket_timeout | CLI 60 | 60 seconds |

FPM: ondemand, max_children=4, idle timeout=10s, max_requests=100,
request_terminate_timeout=10s, `.php` only, kqueue. Original packaged pool used
www, TCP 9000, dynamic/5 children, no request-termination timeout. The chosen
small pool is a local approximation, not a provider concurrency value.

Apache: event MPM, ServerLimit=2, ThreadsPerChild=16, MaxRequestWorkers=32,
MaxConnectionsPerChild=1000; Timeout=30, ProxyTimeout=15; keepalive 5s/100 requests;
request body 10 MiB, 100 fields, 8190-byte field/line limits; request-read timeouts
header=10–20s (500 B/s), body=20s (500 B/s). Configuration parses and effective
modules/run configuration were inspected. Not every ceiling was load-tested.

Bounded enforcement probes: oversized 8300-character URI returned 414. A CPU loop
returned 500 after 4.994s and logged PHP's five-second maximum. `sleep(20)` was
terminated by FPM after 11.160s with HTTP 503 and a corresponding timeout log;
its 10-second setting is not a precise wall-clock deadline. Probe files were
removed. An earlier CPU sample overlapped a service restart and was discarded;
these final samples ran without concurrent service mutation.

Dedicated-user shell soft/hard: 234450 open files and 12171 processes. procstat
reported these same FD/process limits for Apache/FPM/MariaDB masters. Kernel:
maxfiles=260506, maxfilesperproc=234450, maxproc=13524, maxprocperuid=12171.
No kernel tuning or resource exhaustion test. MariaDB max_connections=20,
local_infile=OFF. All values are local configuration/observations; actual
Hostpoint limits and enforcement remain unknown here.

## Lifecycle and reproducibility boundary

Canonical Owner evidence already proves whole-vDisk + UEFI NVRAM **bare-v1**
reproduction on the existing domain: capture 7s, dirty shutdown 9s, offline restore
8s, boot-to-pinned-SSH 21s; disk/NVRAM identity and disappearance of persistent
dirty markers verified. The inactive domain XML was preserved (SHA256
`d8239a990391ffe286d777e3a8e62bbafa71fb0c0b8d31292ee5f42a26786377`). Owner later
attested verified `admin-ready-v1` before packages. CODEX does not claim direct
inspection of these protected host copies or a new runtime baseline capture.

Host evidence: domain `aidumo-freebsd-hostpoint-01`, UUID
`2b2548ae-f019-3837-4924-41d745444ba9`, 4 vCPU/8 GiB, 80-GiB sparse raw disk
`/mnt/cache/domains/aidumo-freebsd-hostpoint-01/vdisk1.img` on Btrfs, exposed via
`/mnt/user/domains/...`; OVMF plus writable NVRAM
`/etc/libvirt/qemu/nvram/2b2548ae-f019-3837-4924-41d745444ba9_VARS-pure-efi.fd`.
Baseline root is `/mnt/cache/domains/.aidumo-b3-baselines/aidumo-freebsd-hostpoint-01/`.
Unraid capture/restore stays Owner-operated, offline only. Reject existing output
paths explicitly, preserve disk/NVRAM/XML together, retain rollback, verify disk
with `qemu-img compare` and NVRAM with `cmp`, then boot and verify the pinned guest.
Never infer host snapshot support from guest ZFS or overwrite retained baselines.

New guest-root inspection found `/var/log/bsdinstall_log`: bsdinstall ZFS stripe
on vtbd0, GPT/260-MiB EFI/512-KiB boot/2-GiB swap/remainder zroot, and distribution
fetch/extraction steps. This corroborates the live partition/dataset layout.
Attached read-only CD contents and device SHA256 were measured:
`fa27646f05a1440fd26ffbb85e06a50bc86e128242a4e9cb7bb3ea76e1aa5fd9`.
Owner identified the host file as `FreeBSD-15.1-RELEASE-amd64-disc1.iso`.
This identifies the **currently attached media**, not independent verification of
its download origin or proof it has never been replaced since installation.
The temporary read-only mount was removed. Raw installer logs are not published.

Reproduction evidence is the retained image restore on this existing domain.
An independent installation from a verified upstream ISO, or recreating a deleted
libvirt definition on a new host, has not been demonstrated. Do not claim those
stronger forms of reproducibility from the reset result.

All three rc services were restarted and the functional probes passed with the
same DB/file markers. Guest root then scheduled `shutdown -r +1` at 18:47:29 UTC
for 18:48:29. SSH was observed unavailable during reboot. Boot epoch changed from
1790617408 to 1790621329; pinned root returned at approximately 18:48:59.6 UTC
(~31s after the scheduled reboot; polling gives an upper-bound observation), then
pinned aidumo returned uid 1001. Both reported the expected hostname and all three
15.1-RELEASE values. Apache, FPM and MariaDB started through rc without intervention;
full HTTP/HTTPS/PDO/filesystem verification passed afterward. These are one
service-restart cycle and one guest reboot, not reliability statistics. No Unraid
operation was needed. No post-profile whole-image reset was performed.

## Reapply the bounded profile

Only on the known dedicated guest after inspecting current state and satisfying
[package prerequisites](runtime-preparation.md), copy `profile/` over pinned SSH
to root-owned staging and run `sh profile/install.sh`. The one-time script refuses
an existing profile, b6web account or initialized MariaDB directory. It backs up
Apache/FPM/rc.conf under `/root/b6-before-profile`, creates only the stated paths,
local certificate, user and fixture DB state, validates configs and uses existing
rc services. It does not bootstrap packages, reset state or touch SSH/host control.
Review any partial failure instead of blindly retrying or deleting guards.

The live installation used these commands plus diagnosed configuration corrections;
final repository configs/fixtures are byte-matched to the guest. The final one-time
script is syntax/review checked, not separately executed against a second fresh VM.
Run `sh profile/verify.sh` as guest root for bounded repeat checks. It drops only
its own newly created `b6_fixture` and preserves restart markers. Host state,
private keys, databases, package caches and logs remain outside the checkout.

## Local versus provider evidence

| A — proven on this VM | B — chosen local approximation | C — provider-only qualification remains |
| --- | --- | --- |
| PHP 8.3 CLI/FPM/modules, Composer/PHAR | Package build, pool user, limits and paths | Exact Hostpoint build/modules/paths, maintenance policy |
| Apache/FPM, real rewrite, public/private separation, headers, TLS | Event MPM, socket topology, loopback ports, local cert | Provider proxy/topology, override policy, certificates/renewal, real Host/forwarding behavior |
| MariaDB 11.4 and ordinary-user PDO fixture | Local socket identity auth, bounded schema grants | Provider password/account policy, remote DB/TLS, versions and limits |
| ZFS case/rename/flock/mode examples | Root-owned public source, private b6web path | Hosting ownership, quotas, jails, backups, network filesystems |
| Service/guest restart and retained bare reset evidence | Local rc settings and retained test markers | Provider lifecycle, availability, operational/recovery behavior |

No Suite application, browser journey, frontend build, External Tester, provider
integration, Hostpoint acceptance, repository setting change or merge is part of
this profile. Mandatory Suite local qualification and real provider smoke remain.

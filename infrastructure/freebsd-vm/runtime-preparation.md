# FreeBSD runtime preparation for #6

Continue only `codex/6-freebsd-vm-substrate` / [PR #13](https://github.com/Innovestro/aidumo-development-infrastructure/pull/13).
CODEX performs non-root work through the existing pinned SSH identity. Owner alone
performs guest-root console and Unraid/libvirt actions. No root password, standing
root, sudo/doas, Docker socket or libvirt access is needed by CODEX.

## Current evidence and pre-install gate

[Issue #6](https://github.com/Innovestro/aidumo-development-infrastructure/issues/6)
records bare-v1 capture (7 s), start-to-pinned-SSH (21 s), persistent dirty state,
ACPI shutdown (9 s), offline restore (8 s), identical disk/NVRAM and clean restored
state: dirty directory absent, zroot ONLINE without errors, DHCP .150 retained,
runtime still bare. This supersedes the stage-2 discovery/reset blockers in the
historical baseline. Retain bare-v1 and the dirty rollback.

Owner then changed the console keyboard and root password locally. Neither secret
nor password database contents are evidence to publish. The issue explicitly
requires a separate **admin-ready-v1** before package bootstrap. At preparation
time, no completed capture evidence was present in its 46 comments or PR #13.
The claim named admin-ready-baseline records admin access, not a completed capture.

Smallest remaining Owner action, if it has not already happened: cleanly shut down
the guest, confirm libvirt `shut off`, and keep it off while capturing the same
three state components as bare-v1 into a fresh protected directory:
`/mnt/cache/domains/.aidumo-b3-baselines/aidumo-freebsd-hostpoint-01/admin-ready-v1`.
Use the proven sparse-copy procedure, retaining ownership/modes:

- raw disk `/mnt/cache/domains/aidumo-freebsd-hostpoint-01/vdisk1.img`;
- NVRAM `/etc/libvirt/qemu/nvram/2b2548ae-f019-3837-4924-41d745444ba9_VARS-pure-efi.fd`;
- inactive XML for domain `aidumo-freebsd-hostpoint-01`.

Explicitly reject an existing destination before copying; never overwrite bare-v1
or capture a running disk. Verify disk with `qemu-img compare`, NVRAM with `cmp`,
record XML checksum and capture duration, then start the VM. Keep copies protected
outside checkouts: the disk includes the root password hash. Publish only sanitized
verification results in #6/PR #13. If already captured, consume the Owner's verified
result instead of repeating capture. No new dirty/reset experiment is required.

Pinned SSH attempts on 2026-09-28 during preparation returned connection timeout,
then `No route to host`, before authentication. The configured pin and identity
remain present; no weakening/replacement was attempted. Therefore **no fresh guest
package/runtime observation is claimed**. The last successful bare observation
found `/usr/sbin/pkg` only (bootstrap stub), no `/usr/local/sbin/pkg` or pkg-static,
no `/var/db/pkg/local.sqlite`, and no standard local runtime binaries. Reconfirm
before running the installation block. A powered-off VM is possible, not proven.

CODEX runs this read-only probe once transport is restored; it never invokes pkg:

```sh
ssh -F /etc/codex-ssh.conf aidumo@192.168.40.150 'sh -s' <<'GUEST'
date -u
id
freebsd-version -kru
uname -m
for p in /usr/sbin/pkg /usr/local/sbin/pkg /usr/local/sbin/pkg-static \
  /var/db/pkg /var/db/pkg/local.sqlite /usr/local/bin /usr/local/sbin; do
  if test -e "$p"; then ls -ld "$p"; else printf 'ABSENT %s\n' "$p"; fi
done
for c in php php-fpm httpd apachectl nginx mysql mariadb mysqld mariadbd \
  sqlite3 git composer node npm cc clang make sudo doas; do
  command -v "$c" || printf 'ABSENT %s\n' "$c"
done
cat /etc/pkg/FreeBSD.conf
zpool status
sockstat -46l
ifconfig vtnet0 inet
test ! -e /home/aidumo/.aidumo-b3-reset-proof && echo DIRTY_DIRECTORY_ABSENT
GUEST
```

A bootstrap stub is not installed pkg. A directory alone is not a package database.
Absent PHP/Git/Node does not establish that FreeBSD base `cc`/`clang`/`make` are
absent: report them separately. This is bounded PATH/standard-path inspection,
not a search for hidden custom installations. If actual pkg already exists, CODEX
may use its absolute path with `query` for local inventory and `rquery -U` against
existing metadata; do not invoke `/usr/sbin/pkg` or refresh metadata as non-root.

## Authority-derived package set

Read-only Suite authority was resolved to full SHA
`dcdea09ffd16cb20485d369772aac018451483de`:

- [Fresh-install deployment](https://github.com/Innovestro/aidumo-suite/blob/dcdea09ffd16cb20485d369772aac018451483de/docs/deployment/hostpoint-fresh-install.md):
  PHP 8.3 web/CLI, required modules, Composer install, public document root,
  private writable bootstrap storage, HTTPS, separately built frontend artifact.
- [Existing local profile](https://github.com/Innovestro/aidumo-suite/blob/dcdea09ffd16cb20485d369772aac018451483de/.github/hostpoint/README.md):
  Apache real `.htaccess`/rewrite, MariaDB 11.4 and exact-certificate HTTPS probes;
  its executable profile remains workstation-local and its qualification gate
  is not replaced by this VM.
- [composer.json](https://github.com/Innovestro/aidumo-suite/blob/dcdea09ffd16cb20485d369772aac018451483de/composer.json):
  PHP ^8.3 / Laravel ^12.0. The development `setup` script runs migrations/npm;
  it must not be used as the fresh-install deployment path.

| Exact requested package names | Reason |
| --- | --- |
| `php83` | PHP 8.3 CLI and FPM in one FreeBSD package; require both build options. Includes hash/json/libxml/openssl/pcre capabilities, checked after installation. |
| `php83-ctype php83-curl php83-dom php83-fileinfo php83-filter php83-intl php83-mbstring php83-pdo php83-pdo_mysql php83-session php83-sodium php83-tokenizer php83-xml php83-xmlreader php83-xmlwriter php83-zip` | Explicit deployment capability list, using FreeBSD's split extensions. |
| `php83-phar php83-composer` | Composer's PHAR dependency and PHP-8.3-flavored Composer for the actual dependency/platform-check deployment path. Never run Composer as root. |
| `apache24` | Apache 2.4, real `.htaccess`/rewrite, proxy_fcgi to FPM, SSL/headers; no mod_php or second webserver. |
| `mariadb114-client mariadb114-server` | MariaDB 11.4 CLI and server for a later isolated ordinary-user SQL/PDO test path. |

These are **22 direct packages**, plus pkg bootstrap if absent and resolver-required
transitive dependencies. No blanket php83-extensions metapackage. No Node/npm,
Git, standalone SQLite CLI, compiler/build tooling, nginx, or separate TLS package
is requested. The existing base OpenSSL is sufficient for local certificate
creation. bcmath/SQLite/pcntl in the Linux profile support its focused test suite;
that suite is not being installed/run in this substrate preparation. Revisit only
if a concrete subsequent probe needs them. Do not copy provider versioned paths
or create compatibility symlinks before measuring FreeBSD's actual paths.

Package naming/options were checked against the FreeBSD ports source at
`b69422ee13d6ad4eb8e0e27b994f8a7abc816235`:
[PHP](https://github.com/freebsd/freebsd-ports/blob/b69422ee13d6ad4eb8e0e27b994f8a7abc816235/lang/php83/Makefile),
[Composer](https://github.com/freebsd/freebsd-ports/blob/b69422ee13d6ad4eb8e0e27b994f8a7abc816235/devel/php-composer/Makefile),
[Apache options](https://github.com/freebsd/freebsd-ports/blob/b69422ee13d6ad4eb8e0e27b994f8a7abc816235/www/apache24/Makefile.options),
[MariaDB](https://github.com/freebsd/freebsd-ports/blob/b69422ee13d6ad4eb8e0e27b994f8a7abc816235/databases/mariadb114-server/Makefile).
Ports definitions do **not** prove binary availability in the guest's configured
ABI/repository. That check remains in the root block, after metadata refresh;
no patch versions are invented. Missing candidates stop the entire runtime install,
with no automatic repository switch, alternative major version or ports build.

## One Owner FreeBSD-console root block

**Hold until admin-ready-v1 verification is recorded and CODEX has completed the
fresh pinned non-root probe above.** This block is preparation, not executed by
CODEX. It checks guest identity, requires Owner baseline acknowledgement, bootstraps
only absent pkg, refreshes configured metadata, resolves every exact name uniquely,
checks PHP CLI/FPM, then fetches the complete dependency solution before install.
It installs exact resolved name-version candidates without a second metadata
refresh. Any failed command exits the child shell. Missing package checks occur
before runtime installation (pkg bootstrap/metadata themselves are intentional
mutations). Installation is not transactional if an installation script fails.
No rc.conf edits, service starts, DB initialization, users, SSH or root-policy
changes are performed by this block; normal package files/accounts are installed.

```sh
/bin/sh <<'B6_ROOT'
set -eu
export PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin
fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || fail 'Owner console root required'
[ "$(hostname)" = aidumo-freebsd-hostpoint-01 ] || fail 'wrong guest'
[ "$(uname -m)" = amd64 ] || fail 'unexpected architecture'
[ "$(freebsd-version -u)" = 15.1-RELEASE ] || fail 'reinspect changed OS'
printf 'Only after verified admin-ready-v1 and CODEX fresh inspection, type admin-ready-v1-verified: ' > /dev/tty
IFS= read -r b6_ack < /dev/tty
[ "$b6_ack" = admin-ready-v1-verified ] || fail 'baseline gate not acknowledged'
if [ -x /usr/local/sbin/pkg ]; then
  b6_pkg=/usr/local/sbin/pkg
elif [ -x /usr/local/sbin/pkg-static ]; then
  b6_pkg=/usr/local/sbin/pkg-static
else
  [ ! -e /var/db/pkg/local.sqlite ] || fail 'database exists without pkg; inspect first'
  /usr/sbin/pkg bootstrap -y
  b6_pkg=/usr/local/sbin/pkg
fi
[ -x "$b6_pkg" ] || fail 'pkg bootstrap did not produce executable pkg'
export REPO_AUTOUPDATE=NO HANDLE_RC_SCRIPTS=NO
"$b6_pkg" update -f
b6_names='php83 php83-ctype php83-curl php83-dom php83-fileinfo php83-filter
php83-intl php83-mbstring php83-pdo php83-pdo_mysql php83-session php83-sodium
php83-tokenizer php83-xml php83-xmlreader php83-xmlwriter php83-zip
php83-phar php83-composer apache24 mariadb114-client mariadb114-server'
set --
for b6_name in $b6_names; do
  b6_row=$("$b6_pkg" rquery -U -e "%n = \"$b6_name\"" '%n %v')
  [ -n "$b6_row" ] || fail "missing candidate: $b6_name"
  [ "$(printf '%s\n' "$b6_row" | wc -l | tr -d ' ')" = 1 ] || fail "ambiguous candidate: $b6_name"
  [ "${b6_row%% *}" = "$b6_name" ] || fail "name mismatch: $b6_name"
  b6_version=${b6_row#* }
  [ -n "$b6_version" ] || fail "empty version: $b6_name"
  printf 'CANDIDATE %s-%s\n' "$b6_name" "$b6_version"
  set -- "$@" "$b6_name-$b6_version"
done
b6_options=$("$b6_pkg" rquery -U -e '%n = "php83"' '%Ok=%Ov')
printf '%s\n' "$b6_options" | grep -qx 'CLI=on' || fail 'PHP CLI unavailable'
printf '%s\n' "$b6_options" | grep -qx 'FPM=on' || fail 'PHP FPM unavailable'
"$b6_pkg" install -n -U "$@"
"$b6_pkg" install -F -y -U "$@"
"$b6_pkg" install -y -U "$@"
# Exact full inventory includes pkg and transitive dependencies.
"$b6_pkg" query -a '%n-%v'
/usr/local/bin/php -v
/usr/local/bin/php -r 'if (PHP_MAJOR_VERSION !== 8 || PHP_MINOR_VERSION !== 3) { exit(1); } foreach (explode(" ", "ctype curl dom fileinfo filter hash intl json libxml mbstring openssl pcre PDO pdo_mysql session sodium tokenizer xml xmlreader xmlwriter zip Phar") as $m) { if (!extension_loaded($m)) { fwrite(STDERR, "MISSING: $m\n"); exit(1); } } echo "PHP_CAPABILITIES=PASS\n";'
/usr/local/sbin/php-fpm -v
/usr/local/sbin/httpd -v
/usr/local/bin/mariadb --version
printf 'PACKAGE_STAGE_COMPLETE; services remain unconfigured by this block\n'
B6_ROOT
```

Do not change the block to skip missing packages. Retain sanitized candidate,
transaction and version output. A package failure is not a runtime PASS.

## CODEX resumes after installation

Through pinned non-root SSH, inventory exact installed versions/modules/paths,
Composer version, FPM binary/config, Apache available modules and MariaDB binary
versions. Inspect readable defaults and listeners before changing configuration.
Then prepare only the minimal isolated fixture/configuration needed for Apache
`.htaccess` and FPM requests, private writable paths, ordinary-user SQL/PDO, and
local HTTPS with the exact certificate trusted. Prefer unprivileged fixture ports
and user-owned state where feasible; return only genuinely required privileged
changes to Owner. Do not deploy or modify Suite to establish a substrate profile.

Measure CLI versus FPM limits separately (memory, execution/input time, upload/post
size, FPM children/request timeout and Apache timeout/request limits), permissions,
case/rename/locking behavior, and bounded restart persistence. Package defaults do
not establish Hostpoint limits or hosting-user execution semantics. Real provider
paths/ownership, account isolation, quotas, proxy topology, certificates, remote
DB/TLS and operational limits remain provider-only. Full #6 runtime acceptance
and VM recreation provenance remain outstanding; no merge/closure is authorized.

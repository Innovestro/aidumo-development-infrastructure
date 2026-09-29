# Native Linux qualification (#19)

Authority: [#19](https://github.com/Innovestro/aidumo-development-infrastructure/issues/19)
under [Program #1](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1).
Run only inside `aidumo-linux-runner-01`, through the existing pinned SSH configuration.
Standing noninteractive guest administration is authorized by #19. No host,
libvirt, other-VM or Suite governance authority follows from that grant.

## Profile derived from Suite

Selected Suite main: `dcdea09ffd16cb20485d369772aac018451483de`.
Read its `composer.json`, `composer.lock`, `package.json`, `package-lock.json`,
`phpunit.xml`, `.github/workflows/pr-validation.yml`, `ci_scope.py`,
`run_mariadb_validation.py` and testing-quality standard before refreshing this
profile. The local commands prove B capability; they do not replace Suite's
required hosted exact-head qualification, review or integration gates.

| Requirement | Native implementation |
| --- | --- |
| Workflow PHP 8.3, Composer v2 | PHP 8.3.35 CLI built from official source; Composer 2.10.3 PHAR |
| Workflow extensions | mbstring, bcmath, PDO SQLite/MySQL; mysqlnd; default CLI extensions include the lockfile's DOM/XML/XMLWriter, ctype, fileinfo, filter, hash, iconv, JSON, libxml, PCRE, Phar, session and tokenizer |
| Direct runtime/install needs | OpenSSL, curl, zip/zlib, sodium; pcntl for process/concurrency tests; readline for CLI |
| Frontend Node 22 | Official Node 22.23.3 distribution, including npm; Suite uses native TypeScript stripping |
| Workflow MariaDB 11.4 | Official 11.4.13 Linux systemd binary distribution; one native loopback-only service |
| Tooling | Existing Git/Python; distro compiler/pkg-config and development libraries needed to build PHP; unzip; Python venv for Suite's own pinned tooling requirements |

Ubuntu 26.04 defaults (PHP 8.5, MariaDB 11.8) are deliberately not substituted
for the workflow's minor versions. Ubuntu Node 22.22.1 failed the actual frontend
lane because it was built without TypeScript support; use the upstream binary.
No Docker, Sail execution, FPM, web server, runner registration, scheduler or
orchestration layer is needed by this qualification path. Laravel Sail's presence
in the dev lockfile alone is not a Docker requirement.

## Bootstrap and execute

1. Verify `sudo -n /usr/bin/id -u` returns `0`, and
   `sudo -n /usr/sbin/visudo -c` succeeds. Validate the installed
   `/etc/sudoers.d/99-aidumo-codex-admin` explicitly as well. Do not print credentials.
2. Transfer and run [bootstrap.sh](bootstrap.sh) as `aidumo`. Downloads are
   SHA-256 checked against pinned official release digests before use. It installs
   under `/opt/aidumo-b19`, with build/download state in `/home/aidumo/b19/downloads`.
   This is a bounded bootstrap, not a package reconciler or drift repair service.
3. Transfer and run [database.sh](database.sh). It initializes only the dedicated
   `/var/lib/aidumo-b19-mariadb` directory and preserves an existing database.
   Its enabled systemd unit is `/etc/systemd/system/aidumo-b19-mariadb.service`.
   Server UID is `b19-mysql`, socket `/run/aidumo-b19-mariadb/mysql.sock`, TCP
   `127.0.0.1:3306`. It ignores unrelated MySQL option files via `--no-defaults`.
4. Transfer an exact-revision Git bundle from the B executor. Never transfer its
   GitHub token, deploy keys, CODEX auth or agent state. Clone under
   `/home/aidumo/b19/suite`, remove the local bundle remote, verify HEAD and a clean
   tracked tree. Copy `.env.example` to `.env`, touch `database/database.sqlite`.
5. Set PATH as below; run `composer install --no-interaction --prefer-dist
   --no-progress`. Never run Suite dependencies or tests with sudo.
6. Run [qualify.sh](qualify.sh) with the absolute Suite directory and lane
   `php`, `frontend` or `mariadb`. Use the workflow time bounds: 1,800, 900 and
   5,400 seconds respectively. Retain exit codes and elapsed times outside Git.
   The MariaDB lane consumes all existing canonical groups without copying their
   commands into B. Only one database qualification may run at a time.

```sh
export PATH=/opt/aidumo-b19/php/bin:/opt/aidumo-b19/node-v22.23.3-linux-x64/bin:$PATH
bash /home/aidumo/qualify.sh /home/aidumo/b19/suite php
bash /home/aidumo/qualify.sh /home/aidumo/b19/suite frontend
bash /home/aidumo/qualify.sh /home/aidumo/b19/suite mariadb
```

For Suite's existing static-tooling lane, create `/home/aidumo/b19/python` with
`python3 -m venv`, install `scripts/requirements-journeys.txt` and
`scripts/requirements-compliance.txt` through that venv's pip, and use its Python.
Use the workflow's exact actionlint 1.7.7 URL and SHA-256 verification, extracting
only `actionlint` into `/home/aidumo/b19/bin`. Run the workflow's existing tooling
and localization commands; no B-owned copy of the tests is needed. Dependency
audits use the existing `composer audit --no-dev --format=plain` and
`npm audit --audit-level=high` policy. Preserve failures rather than inventing
exceptions or editing Suite.

The fixture names/passwords in `database.sh` and `qualify.sh` are the **public
throwaway values in Suite CI**, not Owner credentials. They are only for this
isolated disposable database. Local root uses Unix-socket authentication; the
TCP root fixture is restricted to loopback. No production data belongs here.
The service is not a hostile-code isolation boundary; #19 explicitly grants
`aidumo` guest administration. Stop it before guest-local reset.

PHP CLI memory is 512 MiB; Suite PHPStan explicitly requests 1 GiB. No web-request,
FPM, Hostpoint or browser-service limits are implied. VM allocation remains the
#5 4-vCPU/8-GiB/80-GiB profile. Archive pins do not self-update; re-read Suite and
upstream releases before a later qualification and record the selected versions.

## Clean state and existing #5 recovery

For trusted bounded qualification, discard the *whole* disposable workspace and
MariaDB data directory between clean runs, including generated caches, SQLite,
node_modules/vendor, test-created schemas, users and database privilege state.
`migrate:fresh` alone cannot reset extra databases/users or workspace pollution.
No shared Composer/npm cache may establish source truth; a clean proof uses new
HOME cache paths and lockfile installs. Retain the dirty workspace/data outside
Git until the clean verification completes; never delete an unrecognized path.

To prove #19 clean-state behavior, deliberately add a persistent workspace marker
and database marker/schema/user, restart the database and guest, and verify those
persist. Then recreate a fresh workspace from the unchanged bundle and fresh
database through `database.sh`. The second run must prove marker/schema/user
absence and execute real Suite qualification again. Canonical results and exact timings are in the
#19 PR, not a local readiness ledger.

This is an application/job-state reset, **not a replacement for the full #5
Owner-operated offline raw-disk + NVRAM restore**. Toolchain, OS and administrator
state survive guest-local reset. Suspected OS/root contamination requires the
existing [#5 recovery](../README.md#owner-capture-and-reset-runbook); do not claim
guest cleanup removes arbitrary privileged contamination. No new host capture or
restore is required for a trusted test workload's clean-state proof.

The retained `clean-v1` predates both this toolchain and the sudoers enablement.
Restoring it intentionally removes them. Owner must re-enable guest administration
through the existing staged path, then CODEX can rerun the bootstrap and provision
fresh job state. A future toolchain baseline capture is optional and Owner-only;
never overwrite `clean-v1` or represent the current guest as already captured.
Keep its sentinel unchanged and verify its recorded hash when relating proofs.

Release/source references: [PHP release metadata](https://www.php.net/releases/),
[Composer versions](https://getcomposer.org/versions),
[Node checksums](https://nodejs.org/dist/v22.23.3/SHASUMS256.txt),
[MariaDB checksums](https://archive.mariadb.org/mariadb-11.4.13/bintar-linux-systemd-x86_64/sha256sums.txt),
[MariaDB native tarball procedure](https://mariadb.com/docs/server/server-management/install-and-upgrade-mariadb/installing-mariadb/binary-packages/installing-mariadb-binary-tarballs).

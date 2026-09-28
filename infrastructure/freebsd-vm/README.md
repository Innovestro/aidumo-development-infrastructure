# FreeBSD local prequalification substrate — #6

This is the measured stage-2 baseline for [#6](https://github.com/Innovestro/aidumo-development-infrastructure/issues/6)
and the existing [PR #13](https://github.com/Innovestro/aidumo-development-infrastructure/pull/13).
It follows [current Owner decisions](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1).
Only dedicated [pinned guest SSH](../codex-unraid/README.md) is available to CODEX.
Unraid discovery and lifecycle remain Owner-operated. No Hostpoint equivalence
or full #6 acceptance is established. GitHub PR evidence remains canonical.

## Measurement and system

Measured from persistent CODEX through `ssh -F /etc/codex-ssh.conf aidumo@192.168.40.150`
on **2026-09-28, approximately 16:37–16:38 UTC**. Commands queried local state;
no external TLS/HTTP/DNS probe, installation, configuration change, synthetic
file, reset or restart was performed. SSH/authentication logs and existing
services can still write. `ntpq -pn` queried the local running daemon only;
its existing external peer activity was not initiated by this characterization.

| Item | Observed value |
| --- | --- |
| Hostname | aidumo-freebsd-hostpoint-01 |
| `freebsd-version -kru` | Three lines, each exactly `15.1-RELEASE` (installed kernel, running kernel, userland) |
| `uname -a` | `FreeBSD aidumo-freebsd-hostpoint-01 15.1-RELEASE FreeBSD 15.1-RELEASE releng/15.1-n283562-96841ea08dcf GENERIC amd64` |
| CPU | `hw.ncpu=4`; `hw.model=AMD Ryzen 5 3600 6-Core Processor` |
| RAM | `hw.realmem=8589934592` (8 GiB); `hw.physmem=8536285184` bytes |
| Virtualization | `kern.vm_guest=kvm`; BOCHS ACPI; VirtIO network, block, console and balloon devices in boot log |
| Boot/uptime | `kern.boottime={ sec = 1790587700, usec = 67473 }`, 2026-09-28 11:28:20 CEST (09:28:20 UTC); uptime 7:09 at initial sample |
| Swap | `/dev/vtbd0p3`, 2.0 GiB, 0 used |
| Identity | uid/gid 1001:1001 aidumo; groups wheel (0), aidumo (1001); home `/home/aidumo`; umask 0022 |

Version/install media provenance and the exact Unraid creation definition remain
unknown. The attached guest CD label is `15_1_RELEASE_AMD64_CD`; that alone does
not prove which installer procedure created this VM.

## Storage, paths and writable state

`geom disk list` reports VirtIO `vtbd0`, identifier `vdisk1`, 85,899,345,920 bytes,
512-byte sectors; `cd0` QEMU DVD-ROM is 1,352,255,488 bytes and is not mounted.
`gpart show` reports GPT on vtbd0:

| Partition | Start / length (512-byte sectors) | Type |
| --- | --- | --- |
| p1 | 40 / 532480 | EFI, 260 MiB |
| p2 | 532520 / 1024 | freebsd-boot, 512 KiB |
| p3 | 534528 / 4194304 | freebsd-swap, 2 GiB |
| p4 | 4728832 / 163041280 | freebsd-zfs, approximately 78 GiB |

`zpool status`: zroot ONLINE on vtbd0p4, zero READ/WRITE/CKSUM errors and no known
data errors. `zpool list -p`: size 83,214,991,360; allocated 690,704,384; free
82,524,286,976 bytes. `df -h /`: 75G size, 656M used, 74G available, 1%.
These pool and dataset capacities have different accounting; they are not host
vDisk allocation measurements. Guest `zfs list -t snapshot` returned no datasets.

| Dataset/mount | Observed mount properties |
| --- | --- |
| zroot/ROOT/default → `/` | zfs, local, noatime, nfsv4acls; readonly=off, canmount=noauto |
| zroot → `/zroot`; zroot/home → `/home`; zroot/home/aidumo → `/home/aidumo`; zroot/usr/src → `/usr/src` | zfs, local, noatime, nfsv4acls |
| zroot/tmp → `/tmp`; zroot/var/tmp → `/var/tmp`; zroot/usr/ports → `/usr/ports` | zfs, local, noatime, nosuid, nfsv4acls; exec=on |
| zroot/var/log, zroot/var/audit, zroot/var/crash → corresponding `/var` paths | zfs, local, noatime, noexec, nosuid, nfsv4acls |
| zroot/var/mail → `/var/mail` | zfs, local, nfsv4acls; atime=on |
| `/dev/gpt/efiboot0` → `/boot/efi` | msdosfs, local; fstab rw; 256M size, 1.3M used, 255M available |
| devfs → `/dev` | devfs |

Other datasets zroot/ROOT, zroot/usr and zroot/var are not mounted.
All listed ZFS datasets report casesensitivity=sensitive, normalization=none,
utf8only=off, quota=none and compression=on. These properties support local
case-sensitive path checks; no synthetic rename, Unicode, symlink, locking or
PHP include-path experiment was run. `getconf NAME_MAX /` is 255 and PATH_MAX is
1024. `/usr/home` is absent; do not assume it aliases `/home`.

`/` and `/home` are root:wheel 0755; `/home/aidumo` aidumo:aidumo 0755;
`/tmp` and `/var/tmp` root:wheel 1777. `getfacl` on `/`, `/tmp`, and the home
shows owner/group/everyone NFSv4 entries consistent with those modes. No web user
ownership convention exists yet. Home top-level inspection (excluding SSH and
history contents) found shell/mail defaults. This is not a whole-disk audit.

`/tmp` is writable, executable, disk-backed ZFS, not tmpfs; setuid is disabled.
`sysrc clear_tmp_enable` is NO, clear_tmp_X YES; default periodic daily tmp cleanup
is NO, with no `/etc/periodic.conf`, `/etc/periodic.conf.local` or rc.conf.local.
This establishes configuration, not a reboot persistence experiment. Files in
root/home/tmp/var datasets, EFI contents and swap are mutable disk state. All
must be covered by later whole-vDisk reset; NVRAM/TPM outside it remain unknown.
Guest ZFS and absence of guest snapshots prove nothing about host snapshots.

## Network, TLS, time, services and privilege

| Item | Observed value / limit |
| --- | --- |
| Interface | vtnet0 UP/RUNNING, MTU 1500, MAC `52:54:00:f1:8e:e1`, `192.168.40.150/24`; IPv6 disabled on vtnet0; lo0 IPv4/IPv6 loopback |
| DHCP | `ifconfig_vtnet0=DHCP`; dhclient processes running; lease file exists but is mode 0000 and unreadable. Router reservation is Owner evidence in #1/#6, not independently inspected |
| Routes/resolvers | Default 192.168.40.1; connected 192.168.40.0/24; resolvconf-generated DNS 192.168.40.1, search ris.lan |
| Listeners (`sockstat -46l`) | sshd TCP *:22 IPv4/IPv6; ntpd UDP *:123 and local interface addresses; syslogd UDP *:514 IPv4/IPv6. No web/DB listener observed; firewall reachability not tested |
| Time | Europe/Zurich, CEST UTC+02:00; `/etc/localtime` points to that zone; UTC sample 16:37:53 |
| NTP | ntpd enabled/running, sync_on_start YES; local peer table selected 212.51.144.44 (stratum 1, reach 377, offset -0.023 ms, jitter 0.489 ms). One sample, not a stability guarantee |
| Base TLS | OpenSSL 3.5.6, 7 Apr 2026, FreeBSD-amd64; local TLS 1.3 cipher listing: AES-256-GCM/SHA384, CHACHA20-POLY1305/SHA256, AES-128-GCM/SHA256. No certificate validation, outbound connectivity or negotiated handshake claim |
| SSH | OpenSSH_10.0p2; readable sshd_config active lines: `AuthorizedKeysFile .ssh/authorized_keys`, `Subsystem sftp /usr/libexec/sftp-server`. Unprivileged `sshd -T` fails with `No host key files found`; effective privileged policy remains unverified |
| Admin | wheel permits the PAM su group check; root authentication is still required. `su - root -c /usr/bin/id </dev/null` returned Password/Sorry, exit 1. No working noninteractive escalation found; sudo/doas absent |
| Shutdown policy | `/sbin/shutdown` and poweroff root:operator 04554, reboot root:wheel 0555, su root:wheel 04555. aidumo is not in operator. Owner-authenticated root can later use `/sbin/shutdown -p now` or `/sbin/shutdown -r now`; neither was run |

`sysrc -a` explicitly enables sshd, ntpd and ZFS (plus DHCP); dumpdev=AUTO.
`service -e` also lists base boot/storage/network facilities (hostid, zpool,
zfsbe, var_run, zpoolupgrade/reguid, zvol, devmatch, cleanvar, rctl, ip6addrctl,
netif, devd, resolv), cleanup/log facilities (virecover, gptboot, cleartmp,
dmesg, motd, os-release, newsyslog, syslogd, savecore, utx, bgfsck), kldxref,
mixer and cron. Enabled boot scripts are not all persistent daemons.
Process inspection confirms dhclient, devd, syslogd, ntpd, sshd, cron and getty.
sshd/ntpd/devd status succeeds. cron/syslogd status misleadingly says not running
because their PID files are permission-denied; their processes (and syslogd
sockets) are present. Do not report these as failed services or claim a global
zero-failure count. Boot log warns about virtual L3 cache topology and the
Giant-locked psm device; no remediation attempted. Full service/log audit and
ACPI shutdown behavior remain unproven despite an ACPI power button being visible.

## Packages and existing limits

Safe package detection used filesystem checks only: `/usr/sbin/pkg` exists,
but `/usr/local/sbin/pkg`, pkg-static and `/var/db/pkg/local.sqlite` do not.
The base bootstrap stub was **never invoked**. `/usr/local/bin`, sbin and
etc/rc.d are absent. Thus no bootstrapped pkg installation or registered
third-party inventory was found; no package count is invented.

PHP CLI/FPM, Apache/httpd/apachectl, nginx, MariaDB/MySQL client/server, sqlite3,
Git, Composer, Node/npm, sudo and doas are all absent on PATH; standard local
binary directories are absent, and `/usr/bin/*sqlite*` has no match. This is a
bounded absence check, not proof against custom binaries hidden elsewhere.
Base OpenSSL/SSH are present as above. No PHP limits can be measured yet.

For the remote `sh` process, `ulimit -Sa` and `-Ha` agree: 12,171 processes,
234,450 open files; data 33,554,432 KiB, stack 524,288 KiB, locked memory 64 KiB.
CPU time, file/core sizes, RSS, virtual memory, swap, socket buffer, PTYs,
kqueues, shared locks and pipe buffer report unlimited. sysctl:
`kern.maxfiles=260506`, maxfilesperproc=234450, openfiles=84 (sample),
maxproc=13524, maxprocperuid=12171, argmax=524288.
These are existing limits, not safe workload targets or measured concurrency.
No tuning, stress test, PHP request/process limits or provider limits are claimed.

## Hostpoint-like boundary

| A — measurable/simulatable locally | B — requires deliberate later setup | C — actual Hostpoint evidence this VM cannot prove |
| --- | --- | --- |
| FreeBSD/amd64, ZFS properties, permissions, local path limits | Representative application paths/users; case/Unicode/locking tests | Provider deployment paths, ownership, quotas, backups, account/jail constraints |
| Base shell/process/FD limits | Workload resource and concurrency tests; PHP limits | Actual provider request/process/time/resource limits and enforcement |
| No PHP or FPM installed | Choose PHP version/modules/defaults, CLI/FPM and restart probes | Exact provider PHP build/modules/defaults and maintenance behavior |
| No HTTP server installed | Smallest required Apache or nginx setup; rewrite/.htaccess tests as applicable | Provider topology, proxy behavior and .htaccess policy |
| No DB tools/services installed | Choose required DB client/server and SQLite scope; compatibility probes | Provider DB versions, service/account limits and access policy |
| Local DHCP/routes/listeners, OpenSSL cipher capability and NTP state | Local HTTP/TLS endpoint/cert setup, bounded network tests | Provider inbound/outbound firewall policy, TLS/certificate automation |
| cron process exists; guest writable state mapped | Deliberate cron/background job and clean restart/reset proof | Provider cron/background-process policy, provisioning/control panel, maintenance/restarts |

All C properties are **unknown/provider-only** here; no exact Hostpoint values
have been supplied. The smallest current substrate is this bare guest plus
pinned SSH. A later minimal web stack should be chosen from actual workload
requirements and authoritative provider evidence; installing both webservers or
a generic provider framework is not justified by this characterization.

## Owner-only Unraid discovery next

Run these read-only commands in the **Owner's Unraid Bash terminal**, never in
CODEX. No shutdown, start, snapshot, capture or restore is requested now. Do not
assume the guest hostname equals the libvirt domain name. First list domains and
match the guest MAC against each domain interface list:

```bash
virsh list --all
while IFS= read -r B6_DOMAIN; do
  test -n "$B6_DOMAIN" || continue
  printf '\nDomain: %s\n' "$B6_DOMAIN"
  virsh domiflist "$B6_DOMAIN"
done < <(virsh list --all --name)
```

Set the exact matched name (MAC `52:54:00:f1:8e:e1`), then inspect live/inactive
state. XML output below is limited to relevant device/lifecycle sections; review
locally and redact any credentials before posting evidence.

```bash
B6_DOMAIN='REPLACE_WITH_MAC_MATCHED_DOMAIN_NAME'
virsh dominfo "$B6_DOMAIN"
virsh domstate "$B6_DOMAIN" --reason
virsh domblklist "$B6_DOMAIN" --details
virsh domblklist "$B6_DOMAIN" --inactive --details
virsh snapshot-list "$B6_DOMAIN" --tree
virsh snapshot-current "$B6_DOMAIN" --name
for B6_VIEW in live inactive; do
  if test "$B6_VIEW" = inactive; then
    virsh dumpxml "$B6_DOMAIN" --inactive
  else
    virsh dumpxml "$B6_DOMAIN"
  fi | sed -n -e '/<os>/,/<\/os>/p' -e '/<disk /,/<\/disk>/p' \
    -e '/<tpm /,/<\/tpm>/p' -e '/<on_poweroff>/p' \
    -e '/<on_reboot>/p' -e '/<on_crash>/p'
done
```

A no-current-snapshot error is evidence, not a reason to create one. Record all
writable disks, readonly media, driver formats/backingStore entries, loader,
NVRAM source/template, TPM backend and lifecycle policies. XML policies describe
configured behavior, not a shutdown/start demonstration. dominfo records UUID,
autostart and managed-save state. For an emulated TPM, resolve the actual host
state path locally (including a possible `/var/lib/libvirt/swtpm/<UUID>`), inspect
metadata only, and include it in reset coverage; do not publish TPM contents.

For each file disk from XML, resolve physical storage. If it is under
`/mnt/user`, readlink alone does not resolve Unraid's share filesystem. Substitute
the exact relative path; enumerate matching pool/array files and stop on ambiguous
copies. These commands do not copy or alter an image:

```bash
B6_REL='REPLACE_WITH_PATH_AFTER_/mnt/user/'
for B6_MOUNT in /mnt/*; do
  case "$B6_MOUNT" in /mnt/user|/mnt/user0) continue ;; esac
  if test -f "$B6_MOUNT/$B6_REL"; then
    stat -c '%n %s bytes %U:%G %a' "$B6_MOUNT/$B6_REL"
    findmnt -T "$B6_MOUNT/$B6_REL" -o TARGET,SOURCE,FSTYPE,OPTIONS
    df -hT "$B6_MOUNT/$B6_REL"
  fi
done
# For an already physical source, use its exact path directly with stat/findmnt/df.
```

Do not assume Linux #5's cache path, raw format or NVRAM path applies. Exact
format/backing-chain confirmation using qemu-img is held until a **later Owner
maintenance window** with confirmed clean shutdown. Only then, for each resolved
physical vDisk, run the following read-only inspection while it remains off:

```bash
virsh domstate "$B6_DOMAIN" --reason
# STOP unless state is shut off; prevent concurrent starts during inspection.
B6_DISK='REPLACE_WITH_CONFIRMED_PHYSICAL_VDISK_PATH'
qemu-img info --backing-chain --output=json "$B6_DISK"
qemu-img snapshot -l "$B6_DISK"
du -h "$B6_DISK"
```

Never bypass running-image locks. If XML reports block/network storage, resolve
that actual backend before choosing file-image commands. Record NVRAM/TPM paths,
file ownership/modes and their underlying mount with the same metadata tools.
Do not infer snapshot support from guest ZFS or host filesystem type; libvirt,
internal-image and host-native snapshots are separate, and their complete state
coverage is unproven. If the discovered physical mount is Btrfs, Owner can read
`btrfs subvolume list -s EXACT_MOUNTPOINT`; for a ZFS host pool use
`zfs list -t snapshot -r EXACT_HOST_DATASET`. Select only the matching backend
after discovery; an ordinary file need not be a snapshot-capable subvolume. No host-native snapshot mechanism is needed merely to
proceed to discovery.

After discovery, a separately performed lifecycle proof must use authenticated
Owner guest shutdown, confirm libvirt shut off, measure Owner start to pinned SSH,
and verify clean state. The later guest-root command is `/sbin/shutdown -p now`;
the later Unraid command is `virsh start "$B6_DOMAIN"`, with
`virsh domstate "$B6_DOMAIN" --reason` used to verify both transitions. These
commands are preparation only, not instructions to perform that proof now.
No lifecycle command is executed by this document's
current discovery blocks. Reuse [#5's offline state coverage and verification
principle](../linux-vm/README.md) only after actual FreeBSD host evidence supports
it; its proven timings and shutdown behavior do not transfer to this VM.
Remaining blockers are host state discovery, baseline/recreation provenance,
measured reset/restart, and deliberate PHP/web/DB setup and characterization.

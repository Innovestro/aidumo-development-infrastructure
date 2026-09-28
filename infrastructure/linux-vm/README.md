# Linux VM substrate — #5

This runbook consumes the existing VM under [#5](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5),
[current Owner decisions](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1)
and the single [PR #12](https://github.com/Innovestro/aidumo-development-infrastructure/pull/12).
CODEX uses only [dedicated pinned guest SSH](../codex-unraid/README.md).
Host lifecycle/storage actions belong to Owner. No Suite change, runner install,
package install, sudoers change or host authority is needed for characterization.
PR evidence is canonical; this is an operating runbook, not a readiness ledger.

## Measured guest baseline

Read-only guest inspection on **2026-09-28, 14:05:35–14:05:53 UTC**, from the
persistent CODEX container. Login/audit logs and ordinary service activity still
write normally; “read-only” means no intentional configuration or workload change.
These are observations, not an assertion that the entire VM has been audited.

| Item | Measured result |
| --- | --- |
| OS | `/etc/os-release`: Ubuntu 26.04.1 LTS (Resolute Raccoon), VERSION_ID 26.04, codename resolute |
| Kernel/architecture | `7.0.0-34-generic #34-Ubuntu SMP PREEMPT_DYNAMIC Wed Sep 2 14:29:37 UTC 2026`, x86_64 |
| CPU | 4 online CPUs, KVM, AMD Ryzen 5 3600 model; guest topology 1 socket × 2 cores × 2 threads |
| RAM sample | Total 7,779,495,936 B; available 7,258,775,552 B; used 520,720,384 B |
| Swap | `/swap.img`, 4,294,963,200 B, 0 used |
| Disk | Virtio `vda`, 85,899,345,920 B (80 GiB); `sr0` unmounted ISO9660, 2,927,861,760 B |
| Partitioning | vda1 1,127,219,200 B vfat → /boot/efi; vda2 2,147,483,648 B ext4 → /boot; vda3 82,622,545,920 B LVM2_member |
| Root | `ubuntu-vg/ubuntu-lv`, 82,573,262,848 B, ext4, rw/relatime |
| Free space | Root available 68,955,856,896 B (used 7,583,092,736 B); /boot available 1,814,884,352 B; EFI available 1,118,388,224 B |
| Other mounts | /tmp, /run, /dev/shm, /run/user/1000 and systemd credential mounts are tmpfs; three read-only squashfs snap loops; standard proc/sysfs/devtmpfs/cgroup2/efivarfs mounts. No network or host shared filesystem mount observed |
| Identity | hostname aidumo-linux-runner-01; uid/gid 1000 aidumo; groups adm, cdrom, sudo, dip, plugdev, users, lxd |
| Network | lo; enp1s0 virtio_net, MAC 52:54:00:b2:4c:9e, MTU 1500, 192.168.40.130/24; IPv6 link-local only |
| Routes/DNS | default and DHCP server/DNS 192.168.40.1, metric 100; connected 192.168.40.0/24 |
| DHCP | networkd reports DHCPv4 and acquired .130 at boot; generated Netplan network file selected; DHCP client uses IAID/DUID. Owner confirms router reservation; router configuration not inspected |
| Time | Etc/UTC, RTC UTC; synchronized, chrony active, stratum 3, leap Normal, ~25 μs slow in sample |
| SSH | ssh.socket enabled/active on IPv4/IPv6 port 22; ssh.service active, socket-triggered (service itself disabled); OpenSSH 1:10.2p1-2ubuntu3.6; dedicated pinned login succeeds |
| Privilege/lifecycle | `sudo -n true` exits 1: interactive authentication required; `sudo -n -l` likewise. reboot/shutdown/poweroff binaries exist; login1 CanReboot and CanPowerOff both return “challenge”. No reboot/shutdown executed |
| Cloud-init | 26.1-0ubuntu3~26.04.1 installed, disabled by /etc/cloud/cloud-init.disabled; units loaded/enabled but inactive with unmet conditions |
| Guest agent | qemu-guest-agent package/binary absent in inventory, unit not found; open-vm-tools 2:13.0.10-1ubuntu1 installed (not QEMU guest agent) |
| Health | zero failed units; no /var/run/reboot-required; observed systemd startup 6.031 s (kernel .752 + initrd 2.202 + userspace 3.077) |
| Tools | Git 1:2.53.0-1ubuntu1 and Python 3.14.3-0ubuntu2 already installed. No docker/podman/containerd/nerdctl/gh/node/npm/php/composer/mysql/mariadb/gcc/make/qemu-ga on PATH |
| Workload footprint | No Docker/containerd/actions.runner units observed; /opt and /usr/local/bin empty, aidumo home contains shell defaults, .ssh and .cache. Bounded depth-2 inspection excluded .ssh contents and did not read history |
| Listening sockets | TCP 22 on all addresses, DNS on loopback; UDP DHCP, loopback DNS and chrony. No build/database service observed |

Owner-reported allocation is 8 GiB; the table reports guest-visible MemTotal
rather than treating the difference as unexplained host overcommit. No host
resource sampling or end-to-end boot/reset timing has yet been performed.
Generated network configuration was permission-denied; DHCP behavior is measured
through networkctl/routes/journal, not an inspection of protected Netplan YAML.
Effective root-only sshd/firewall configuration and full root-owned filesystem
contents were not inspected. Absence of a tool in these bounded checks is not a
whole-disk forensic guarantee.

Relevant enabled baseline units: networkd, resolved, chrony, SSH socket, AppArmor,
ufw, cron, rsyslog, snapd, unattended-upgrades, lvm2-monitor, multipathd, open-iscsi,
open-vm-tools, kdump-tools, sysstat and cloud-init units. Enabled does not imply
active or enforcing (in particular ufw policy was not established).
The lxd-installer socket is active; lxd itself is not among installed snaps.
APT daily/upgrade, fwupd-refresh, logrotate, fstrim and sysstat timers are enabled.
Unattended upgrades are active. Automatic package/snap changes can cause drift;
re-measure immediately before capture and after restore. Do not disable them
silently or claim package identity across a drifted run.

### Bounded package inventory

717 installed dpkg packages. Sorted installed name/version/status rows had
SHA-256 `edf7da21eed1a78144a196e70dd9d62c60542c6e09d6607ede7ee5bbbf04683d`.
Reproduce without writing on the guest:

```bash
ssh -F /etc/codex-ssh.conf aidumo@192.168.40.130 'bash -s' <<'GUEST'
dpkg-query -W -f='${binary:Package}\t${Version}\t${db:Status-Status}\n' |
  awk '$3=="installed"' | LC_ALL=C sort | sha256sum
apt-mark showmanual | LC_ALL=C sort
snap list
GUEST
```

Manual packages (21): bash, dash, diffutils, efibootmgr, findutils, grep,
grub-efi-amd64, grub-efi-amd64-signed, gzip, hostname, init, linux-generic,
ncurses-base, ncurses-bin, openssh-server, shim-signed, ubuntu-minimal,
ubuntu-server, ubuntu-server-minimal, ubuntu-standard, util-linux.

Snaps: core24 20260410/revision 1643; hwctl 0.11.1/revision 123;
snapd 2.76.2/revision 27710. No packages or toolchain were installed by stage 2.

## Reset decision and remaining evidence

Use one **powered-off whole-VM baseline**, operated by Owner. Prefer native
Unraid snapshot/revert only after the actual version, disk format/chain,
storage and this VM's available snapshot/revert controls are established.
The guest's ext4/LVM tells us nothing about the host filesystem or vDisk format.
Guest LVM-only reset would omit EFI, /boot and other VM state and is not the
selected approach. No QEMU agent is needed for an offline baseline.

[Unraid's VM documentation](https://docs.unraid.net/unraid-os/using-unraid-to/create-virtual-machines/vm-setup/#vm-snapshots)
describes native snapshot/revert and QCOW2 support.
[Libvirt snapshot semantics](https://www.libvirt.org/formatsnapshot.html)
distinguish internal/external snapshots and disk/memory state. Neither document
proves support on this host. An empty libvirt snapshot list alone does not prove
absence of Unraid-managed snapshots or backing chains.

If native reset is unavailable, the smallest fallback is an **offline protected
disk baseline copy plus offline restore**, retaining the domain definition,
writable UEFI NVRAM and any other attached writable state (e.g. TPM, if present).
For a standalone raw/qcow2 image, use a verified sparse copy; if a backing chain
exists, first specify a complete offline export/restore plan rather than copying
only its active overlay. Restore to a separate verified file while shut off,
retain the dirty disk until boot/verification succeeds, and preserve the original
path/permissions and domain identity. Do not mix Unraid user-share and physical
paths in a copy operation. Disk copies contain credentials and remain protected
outside Git. No filesystem conversion, extra service or orchestration is needed.

**Blocked:** actual host disk/chain/storage and native reset capability are
unknown. Capture, contamination, revert, recreation proof and reset timing are
pending. sudo/agent limitations are not blockers to Owner-operated offline reset.
No concrete capacity or failed-service obstacle was observed in the guest.
An installed ISO remains attached; verify boot order as part of domain inspection.

## Exact next Owner discovery commands

Run only on the **Unraid web terminal**, not in CODEX. These are read-only.
First list domains; do not assume the guest hostname equals the libvirt name:

```bash
cat /etc/unraid-version
virsh version
virsh list --all
```

Set B5_VM to the exact name from that output. Inspect XML locally; share only
disk driver/source/target, loader/NVRAM, TPM, filesystem/hostdev, interface
MAC/source, memory/vCPU, boot and ACPI sections. Do not publish graphics
passwords, metadata containing secrets, or unrelated host state.

```bash
B5_VM='REPLACE_WITH_EXACT_DOMAIN_NAME'
virsh dominfo "$B5_VM"
virsh domstate "$B5_VM" --reason
virsh domblklist "$B5_VM" --details
virsh domblklist "$B5_VM" --inactive --details
virsh dumpxml "$B5_VM" --inactive
virsh snapshot-list "$B5_VM" --tree
virsh pool-list --all --details
virsh help shutdown
virsh help start
virsh help snapshot-create-as
virsh help snapshot-revert
```

Also report whether this VM has native **Create Snapshot** and **Revert**
controls in the Unraid UI, and names/state of any listed snapshots. CLI help
shows command availability, not proof that a particular disk supports it.
For any existing snapshot, inspect locally using
`virsh snapshot-dumpxml "$B5_VM" 'EXACT_SNAPSHOT_NAME'` and return sanitized
disk/parent/state information. UI metadata and backing chains must also agree.

For each writable disk source shown above, set its exact path:

```bash
B5_DISK='REPLACE_WITH_EXACT_DISK_SOURCE_PATH'
readlink -f -- "$B5_DISK"
stat -c 'type=%F bytes=%s blocks=%b blocksize=%B mode=%a uid=%u gid=%g' -- "$B5_DISK"
findmnt -T "$B5_DISK" -o TARGET,SOURCE,FSTYPE,OPTIONS
df -hT -- "$B5_DISK"
```

If the source is under /mnt/user, that is a share view, not proof of the
physical backing filesystem. In the Unraid Shares UI identify the actual
disk/pool containing this file and report its storage/mover settings. Set
B5_PHYSICAL to that confirmed physical file path and repeat findmnt/df:

```bash
B5_PHYSICAL='REPLACE_WITH_CONFIRMED_PHYSICAL_FILE_PATH'
findmnt -T "$B5_PHYSICAL" -o TARGET,SOURCE,FSTYPE,OPTIONS
df -hT -- "$B5_PHYSICAL"
```

For Btrfs run `btrfs filesystem usage "$(dirname "$B5_PHYSICAL")"`;
for ZFS run `zfs list -o name,mountpoint,used,available,refer` and
`zpool status`, returning only the relevant pool/dataset.
For a libvirt-managed pool, run `virsh pool-info 'EXACT_POOL_NAME'`.
Record relevant free space and health; do not infer native VM reset merely
from Btrfs/ZFS availability.

### Owner maintenance window: establish offline disk facts

The following changes VM power state. Run when Owner is ready for this VM's
brief outage; no contamination or snapshot/restore is performed here.
This is the proposed safe path, not a previously proven shutdown:

```bash
date -u --iso-8601=seconds
virsh shutdown "$B5_VM" --mode acpi
virsh domstate "$B5_VM" --reason
```

Wait and repeat domstate until it says **shut off**. A successful shutdown
request is not proof of shutdown. If it remains running, stop this sequence
and use the guest console's authenticated shutdown; do not force-destroy it.
Only while confirmed shut off, inspect each actual disk:

```bash
qemu-img info --backing-chain --output=json "$B5_DISK"
```

Do not bypass image locks with force-share against a running VM. Return disk
format, backing files, actual/virtual size, internal snapshots and any errors.
If there are multiple writable disks/state files, all require baseline coverage.
Restart this same domain after inspection:

```bash
virsh start "$B5_VM"
date -u --iso-8601=seconds
virsh domstate "$B5_VM" --reason
```

Verify pinned SSH from CODEX using the existing command. This establishes the
shutdown/start path, not a reset. Return sanitized results to PR #12; exact
capture/revert commands can then be bound to real paths and supported controls.

## Later bounded dirty → reset → clean proof (not executed)

1. With host facts resolved, record a fresh package digest, manual packages,
   snap revisions, mounts, services, network/clock, CPU/RAM/free-space sample.
   Record clean absence of a uniquely named persistent marker directory under
   /home/aidumo. Create a small baseline sentinel there, record content hash,
   owner and mode, then have Owner shut down and capture the complete baseline.
   Use persistent ext4, not /tmp (tmpfs), so a reboot alone cannot pass.
2. Boot and confirm the baseline sentinel. With the next stage admitted, change
   its contents and create a second harmless marker file in that directory.
   Record both dirty contents/hashes. Install nothing for this proof.
3. Owner performs the selected reset/revert while shut off, then starts the VM.
   Record UTC start/end and elapsed durations for shutdown, capture/restore,
   start-to-pinned-SSH readiness; also record image/overlay storage consumption
   and guest resource samples. Distinguish reset time from initial capture time.
4. CODEX verifies original sentinel contents/owner/mode restored, dirty-only
   file absent, package/manual/snap baseline matches, reserved DHCP address and
   pinned SSH persist, expected mounts/services and synchronized time return.
   Do not manually remove the dirty marker to make verification pass. Expected
   volatile changes (boot ID, logs, uptime, free RAM) are not contamination;
   unexpected package drift must be explained and the affected proof repeated.
5. Record exact baseline identity, host mechanism/paths (sanitized), candidate
   SHA, commands/results and timings in PR #12. Document recreation from the
   protected baseline/domain state. No full #5 PASS until that evidence exists.
   No merge, issue closure, Product acceptance or Suite integration follows
   automatically.

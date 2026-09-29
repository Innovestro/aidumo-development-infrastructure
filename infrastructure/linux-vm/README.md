# Linux VM substrate — #5

This runbook consumes the existing VM under [#5](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5),
[current Owner decisions](https://github.com/Innovestro/aidumo-development-infrastructure/issues/1)
and the single [PR #12](https://github.com/Innovestro/aidumo-development-infrastructure/pull/12).
CODEX uses only [dedicated pinned guest SSH](../codex-unraid/README.md).
Host lifecycle/storage actions belong to Owner. No Suite change, runner install,
package install, sudoers change or added CODEX host authority was needed for #5.

The later [#19 native qualification profile](qualification/README.md) adds the
Suite-derived toolchain and standing guest administration under its own authority.
The measurements below remain the historical bare #5 baseline.
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
| Privilege/lifecycle | `sudo -n true` exits 1: interactive authentication required; `sudo -n -l` likewise. reboot/shutdown/poweroff binaries exist; login1 CanReboot and CanPowerOff both return “challenge”. No reboot/shutdown executed during this initial inspection; later authenticated Owner shutdown proven below |
| Cloud-init | 26.1-0ubuntu3~26.04.1 installed, disabled by /etc/cloud/cloud-init.disabled; units loaded/enabled but inactive with unmet conditions |
| Guest agent | qemu-guest-agent package/binary absent in inventory, unit not found; open-vm-tools 2:13.0.10-1ubuntu1 installed (not QEMU guest agent) |
| Health | zero failed units; no /var/run/reboot-required; observed systemd startup 6.031 s (kernel .752 + initrd 2.202 + userspace 3.077) |
| Tools | Git 1:2.53.0-1ubuntu1 and Python 3.14.3-0ubuntu2 already installed. No docker/podman/containerd/nerdctl/gh/node/npm/php/composer/mysql/mariadb/gcc/make/qemu-ga on PATH |
| Workload footprint | No Docker/containerd/actions.runner units observed; /opt and /usr/local/bin empty, aidumo home contains shell defaults, .ssh and .cache. Bounded depth-2 inspection excluded .ssh contents and did not read history |
| Listening sockets | TCP 22 on all addresses, DNS on loopback; UDP DHCP, loopback DNS and chrony. No build/database service observed |

Owner-reported allocation is 8 GiB; the table reports guest-visible MemTotal
rather than treating the difference as unexplained host overcommit. Host
allocation/storage and measured capture/reset/SSH-readiness timings are recorded
below; no host CPU utilization or load benchmark is claimed.
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

## Proven reset mechanism

The canonical strategy is **Owner-operated offline baseline copy/restore of the
sparse raw vDisk and UEFI NVRAM**. Inactive domain XML is retained as
reconstruction/reference evidence. This is the mechanism actually exercised on
2026-09-28, not a conditional preference for native snapshots. It has no native
snapshot dependency, qcow2 chain, libvirt automation or orchestration platform.
Guest ext4/LVM is inside the disk and is not the host reset mechanism.

### Host and offline state

| Item | Recorded fact |
| --- | --- |
| Host | Unraid 7.3.2; libvirt library/API 12.2.0; QEMU API 12.2.0; QEMU hypervisor 10.2.3 |
| Domain | aidumo-linux-runner-01; UUID 7e4fc744-0375-d793-12fd-0cf7570b94e7; persistent; autostart disabled; no managed save |
| Allocation | 4 pinned vCPUs, 8 GiB RAM, one writable 80 GiB vDisk |
| Physical disk | /mnt/cache/domains/Ubuntu/vdisk1.img |
| Domain disk source | /mnt/user/domains/Ubuntu/vdisk1.img; active/inactive block views agree; host target hdc (guest sees vda) |
| Storage | /mnt/cache on /dev/nvme0n1p1, Btrfs; 932 GiB total, ~450 GiB used, ~482 GiB available at discovery |
| Share | domains uses cache=prefer, pool cache, shareCOW=no; /mnt/user is shfs, not the physical filesystem |
| Offline image | raw; 85899345920 bytes virtual; 4130426880 bytes allocated (~3.85 GiB) at discovery; no backing chain; dirty flag false; no special file attributes observed |
| Disk metadata | Observed mode 0777, root:users; preserved during restore, not a newly recommended permission policy |
| Snapshots | No libvirt snapshots existed; no native snapshot capability is required or asserted |
| Firmware code | Read-only /usr/share/qemu/ovmf-x64/OVMF_CODE-pure-efi.fd |
| Writable NVRAM | /etc/libvirt/qemu/nvram/7e4fc744-0375-d793-12fd-0cf7570b94e7_VARS-pure-efi.fd |
| Other state | No TPM device/state observed in inactive XML; install ISO remains attached at /mnt/user/isos/ubuntu-26.04.1-live-server-amd64.iso |

The observed libvirt elevated-privilege taint is a host runtime property, not a
grant of host authority to CODEX. The VM is a local development substrate, not
an asserted hostile-workload security boundary. No host/network shared filesystem
was observed in the guest. Keep the guest a DHCP client with the Owner reservation
192.168.40.130; do not substitute guest-static addressing.

### Shutdown finding

`virsh shutdown aidumo-linux-runner-01 --mode acpi` at 14:53:43 UTC did not
shut down the VM within 60 seconds. Afterwards TCP/22 accepted connections but
SSH stalled during banner exchange; VNC was not interactively usable. Owner used
one hard stop for recovery **before any baseline existed**. The VM subsequently
booted normally. That event is neither the normal procedure nor reset proof.

Authenticated guest `sudo systemctl poweroff` subsequently worked for clean
capture and dirty-state shutdown, producing libvirt **shut off (shutdown)**.
Always use that authenticated guest path before capture/restore and separately
verify libvirt state. Do not rely on the failed ACPI path, an SSH disconnect, or
successful submission of a shutdown request. If authenticated shutdown fails,
stop the reset procedure for Owner recovery; do not turn hard stop into an
automatic fallback or capture a supposedly clean baseline from that event.

## Owner capture and reset runbook

All host operations below belong to Owner on Unraid. CODEX retains only its
dedicated guest key and strict pinned SSH access; no host root credentials,
Docker/libvirt socket, broad NAS mount or passwordless sudo is added. Disk and
NVRAM copies contain guest credentials and remain in protected host-local storage,
never Git or public evidence. Keep baseline directories Owner-only and do not
publish raw domain XML or credential material.

1. Confirm the exact domain/UUID, disk mapping, NVRAM, firmware/ISO dependencies
   and current physical path against the table. Recheck `virsh domblklist
   aidumo-linux-runner-01 --inactive --details` and inactive XML locally before
   each operation. If writable disks/state or backing storage have changed, stop
   and update coverage. Ensure adequate physical pool space for sparse copies
   and retained dirty state. Do not mix /mnt/user and /mnt/cache paths in copies;
   prevent concurrent starts, configuration changes or mover relocation during
   the Owner maintenance window.
2. For a new baseline only, verify the intended clean guest, record the package
   digest and sentinel metadata, and select a **new** protected baseline directory.
   The existing clean-v1 is retained; never overwrite it with the dirty guest.
   Owner authenticates in the guest and runs `sudo systemctl poweroff`. For both
   capture and restore, confirm `virsh domstate aidumo-linux-runner-01 --reason`
   reports **shut off** before touching any image/NVRAM. Keep it off throughout.
3. Capture the physical raw disk using `cp --sparse=always --reflink=never` into
   the new baseline as `vdisk1.img`; copy NVRAM as `nvram.fd`; retain
   `virsh dumpxml aidumo-linux-runner-01 --inactive` output as `domain.xml`.
   Record active disk/NVRAM ownership and modes for restore. Verify offline disk
   equality with `qemu-img compare -f raw -F raw SOURCE COPY`, require exit 0 and
   `Images are identical.`, compare NVRAM bytes, and record NVRAM/XML SHA256.
   Use `qemu-img info --backing-chain` and `du -h` to confirm raw/no chain and
   sparse allocation. Never bypass running-image locks. No reflink or Btrfs
   snapshot behavior is assumed from the backing filesystem.
4. To reset from **clean-v1**, first confirm authenticated shutdown and shut-off
   state again. Retain the dirty active disk separately at an Owner-recorded,
   unique protected path for rollback/evidence. Preserve its original metadata;
   do not use the clean baseline as a scratch destination. Restore clean-v1's
   `vdisk1.img` to the physical active disk path with
   `cp --sparse=always --reflink=never`, and restore its `nvram.fd` to the exact
   active NVRAM path above. Restore the active ownership/modes recorded before
   replacement. Keep the domain identity and configuration unchanged. A failed
   copy/verification leaves the VM off; do not boot partial state.
5. **Before boot**, compare baseline and restored active raw disks using
   `qemu-img compare -f raw -F raw`, require identical result/exit 0; compare
   baseline and active NVRAM with `cmp` (exit 0). Check NVRAM against its recorded
   SHA256, disk size/format/no backing chain and sparse allocation. Check the
   inactive definition against retained domain.xml for unintended changes.
   XML is reference evidence; routine reset does not redefine the domain.
6. Owner starts the same domain with `virsh start aidumo-linux-runner-01`.
   Measure elapsed time to a successful **authenticated pinned SSH command**,
   not merely an open TCP port. From CODEX use
   `ssh -F /etc/codex-ssh.conf aidumo@192.168.40.130 hostname`.
   Verify the sentinel SHA256/mode/uid/gid/size, absence of the recorded dirty-only
   file, installed-package digest using the command above, zero failed systemd
   units, hostname and reserved DHCP address. Keep dirty-state evidence until
   these checks pass and Owner integration is complete. Never manually repair
   markers to make reset verification pass.

For recreation of this same substrate, restore the disk and NVRAM as above and
use retained domain.xml to reconstruct the definition only if it is missing.
Owner must first check that no conflicting name/UUID exists and that its exact
firmware, disk, network, CPU pinning and ISO references still resolve on Unraid.
Keep the original MAC/UUID and DHCP reservation. The recorded proof recreated
clean mutable state within the existing domain; it did not test deletion and
redefinition of the domain or recovery on a different host. This is a local
baseline recreation procedure, **not disaster recovery**, a fresh installer
reproducibility claim, or a guarantee against loss of the cache pool.

## Retained baseline and measured proof

The retained baseline is:
`/mnt/cache/domains/.aidumo-b2-baselines/aidumo-linux-runner-01/clean-v1`, containing
`vdisk1.img`, `nvram.fd`, and `domain.xml`. The temporary **dirty-before-reset**
vDisk is a distinct rollback/evidence artifact; its exact path was not included
in the supplied evidence and must be resolved from Owner's local record before
cleanup. It must never be mistaken for the clean baseline.

| Evidence | Actual result |
| --- | --- |
| Clean sentinel | /home/aidumo/.aidumo-b2-baseline/sentinel.txt; mode 0600; uid/gid 1000:1000; 28 bytes |
| Clean and restored sentinel SHA256 | 8dd7ec92b0b71613747c4256ef902982a9dd6560f52e254882b647fa6f20d75d |
| Dirty sentinel SHA256 | 54af91309a67a199e1a74c40036827f3dad670795d76130682575b2c59acd706; 0600; 1000:1000; 19 bytes |
| Dirty-only file SHA256 | 48fa9d9ec4d4f9c33bc82f4b38052dbfad08b20917e99a12127929a30863f3b0; 0600; 1000:1000; 37 bytes |
| Package digest, clean/dirty/restored | edf7da21eed1a78144a196e70dd9d62c60542c6e09d6607ede7ee5bbbf04683d |
| Baseline NVRAM SHA256 | c6ce66d7e8ba5b5dac1002a3eabca739231faa95c00b10084f708152af537ad9 |
| Baseline domain XML SHA256 | d64389928762df1b237f9c7a8b76b923195750f54d46725f78a36aa59c3e981a |
| Capture | 30 s, 2026-09-28 15:21:53–15:22:23 UTC; offline sparse non-reflink copy; Images are identical.; baseline allocation 3.8 GiB by du (~3.79 GiB image report) |
| Reset/restore | 43 s, 15:36:48–15:37:31 UTC; dirty disk retained; offline sparse non-reflink restore; active ownership/mode restored; Images are identical.; NVRAM_IDENTICAL=PASS; active allocation 3.8 GiB |
| Start to pinned SSH | 13 s from start request at 15:38:06 UTC |
| Post-reset | Clean sentinel hash and all metadata restored; dirty-only file absent PASS; package digest unchanged; 0 failed systemd units; hostname aidumo-linux-runner-01; DHCP 192.168.40.130/24 |

The contamination was on persistent guest storage, not /tmp: a changed sentinel
and an additional file survived until offline restore. Restoring both original
bytes/metadata and the absence of dirty-only state is the clean-state proof.
The dirty-only pathname/content were not supplied in canonical evidence; do not
invent them. For future cycles record the exact marker pathname before dirtying.
No Docker, GitHub Runner or Aidumo toolchain was installed. Existing distro
packages remain the bootstrap baseline; any later tool bootstrap needs its own
admitted package and new measured baseline.

These are measured timings for one real cycle, not statistical reliability,
shutdown duration, fresh-install duration or a load benchmark. The earlier
6.031 s systemd startup sample is not the measured 13 s end-to-end readiness.
Post-reset package digest/service/network checks are recorded; fresh snap/manual
inventory, clock and mount comparisons were not supplied for this final cycle
and are not claimed. Future baseline updates should recheck those drift sources.

Canonical evidence: [host/storage](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5872327640),
[offline raw image](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5872835395),
[state coverage](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5872888563),
[authenticated shutdown](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5873034335),
[capture](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5873119126),
[dirty state](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5873300073),
[clean verification](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5873428802),
[restore](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5873454849),
[readiness](https://github.com/Innovestro/aidumo-development-infrastructure/issues/5#issuecomment-5873487856).
The Owner's final evidence additionally confirms both copy flags and retained
rollback disk. Technical review and acceptance mapping belong in PR #12/#5.

## Retention and scope

Retain clean-v1 disk/NVRAM/XML for future resets, the active restored disk/NVRAM,
and the dedicated pinned guest SSH access. Only **after Owner integration** and
successful clean verification may Owner remove the identified temporary dirty
rollback/evidence disk and abandoned temporary copy files, after verifying none
is referenced by the domain or the retained baseline. No cleanup runs as part of
this handoff. Keep the install ISO attached for now; detaching it or removing its
file requires checking boot/reconstruction dependencies separately.

No disaster-recovery, Hostpoint equivalence, production or Suite CI binding is
claimed. No GitHub Runner, guest toolchain, automation platform, Suite/C change,
repository settings change, merge or issue closure is part of this handoff.
Owner integration follows the distinct same-agent technical review; that review
is not independent DEV PASS or Product acceptance.

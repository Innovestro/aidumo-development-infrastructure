# Executable infrastructure placement

Development Infrastructure source, tests and non-secret configuration belong
here only for an explicitly admitted capability.

- [codex-unraid/](codex-unraid/README.md): #4, one persistent CODEX executor and
  bounded Unraid pilot. See its Owner runbook and acceptance limits.
- [linux-vm/](linux-vm/README.md): #5, real guest characterization and the
  Owner-operated reset decision/proof procedure; host reset evidence is pending.

Suite contracts remain in A; tester implementation remains in C. Actual secrets,
sessions, logs, journals, databases, volumes and VM images stay in protected
host-local storage outside the checkout, as described in [README.md](../README.md).

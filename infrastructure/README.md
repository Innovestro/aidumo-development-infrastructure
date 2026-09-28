# Executable infrastructure placement

Development Infrastructure source, tests and non-secret configuration belong
here only for an explicitly admitted capability.

- [codex-unraid/](codex-unraid/README.md): #4, one persistent CODEX executor and
  bounded Unraid pilot. See its Owner runbook and acceptance limits.

Suite contracts remain in A; tester implementation remains in C. Actual secrets,
sessions, logs, journals, databases, volumes and VM images stay in protected
host-local storage outside the checkout, as described in [README.md](../README.md).

# Executable infrastructure placement

Future executable Development Infrastructure (B) source, its tests and non-secret
configuration belong here, when an explicitly authorized capability needs them.
Choose the smallest layout for that capability at that time.

B0 supplies this location only. There are no executable components, dependency
manifests, generated scaffolds or placeholder coordinator/runner/VM subprojects.
Suite contracts remain in A; tester implementation remains in C. Actual secrets,
sessions, logs, journals, databases, volumes and VM images stay in protected
host-local storage outside the checkout, as described in [README.md](../README.md).

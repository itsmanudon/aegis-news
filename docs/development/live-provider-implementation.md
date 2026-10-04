# Live multimedia implementation sequence

Scope: manual, bounded local development acquisition through the existing authenticated
ingestion API and Temporal workflow. The user supplied the provider contract, policy
separation, acceptance sequence and authorization to execute on 4 October 2026.

- [x] Review and fast-forward historical loader; push main and wait for hosted CI.
- [x] Replace full-feed intelligence fan-out with bounded cursor pages and lazy detail;
  prove unfiltered Real API behavior against the existing 3,000-record corpus.
- [x] Add optional SecretStr settings and document current official provider contracts.
- [x] Implement bounded allowlisted async transport and five fixture-tested adapters.
- [x] Persist acquisition identities/evidence and remote article media references;
  submit articles through authenticated ingestion; isolate provider failures.
- [x] Store YouTube only as refreshable, expiring references, with deletion/refresh
  controls and retention housekeeping. No video bytes or AI/provenance for API metadata.
- [x] Expose protected manual fetch/status controls and CLI/Doppler invocation.
- [x] Display article attribution/images and separate YouTube references in existing UI.
- [x] Run complete local checks, migration roundtrip, mock and Real API browser tests.
- [x] Perform tiny real acceptance, then bounded demo population and idempotent rerun.
- [x] Record aggregate evidence and commit implementation for hosted review.

Hosted feature CI status is reported in the final handoff.

Review focus: secret-bearing errors, duplicate polls with changed provider snippets,
cross-provider evidence loss, unavailable/malformed publishers, expired/deleted videos,
partial failures and interrupted submissions. Normal CI uses mocked providers and
Offline inference. Main and historical tags remain untouched after reconciliation.

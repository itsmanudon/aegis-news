# Daily Publishing Execution Ledger

## Scope And Baseline

- Owner merged PR #2 on 15 October 2026. Baseline main:
  `6334cc7e213744b0d787a27556e8a74232e32884`.
- Implementation branch: `feat/daily-publication`. PR #2 is retained as merged;
  a follow-up PR will carry this work. No history rewriting or automatic main merge.
- The new owner brief authorizes a once-daily pipeline, replacing the earlier
  manual-only acquisition policy for this next phase.
- Current production remains the validated NASA release until verified integration.
- Target schedule: 06:23 UTC / 11:53 Asia/Kolkata. Activation requires the final
  approved default-branch integration, dedicated signing secret and trust registry.

## Design Decisions

- Extend the existing static publisher; preserve v1 NASA record signatures exactly.
- Use explicit source policies and fixed acquisition endpoints. Publisher links
  are never fetched. Bodies and unlicensed media stay excluded.
- Durable state lives on a dedicated public-data Git branch, with signed release
  envelopes, append-only release history and compare-and-swap updates.
- A separate unattended signing key has a versioned ID. It does not reuse or
  migrate the local showcase key or archive-encryption keys.
- GitHub environments restrict signing/deployment to trusted default-branch code.
- All publication paths share a non-cancelling concurrency group.
- Build and verify before deploying; persist a prepared state before deployment,
  promote its validated release receipt after a successful atomic Pages upload.
  A failed run leaves the current production deployment intact and supports retry.

## Progress

1. Inspected merged PR history, root/nested instructions, v1 contracts, providers,
   crypto, static renderer, workflow, tests and existing credential configuration.
2. Researching provider licensing, endpoint freshness and media-specific rights.
   Commercial provider access alone is insufficient republication permission.
3. Implementation, controlled acquisition, signing, state, browser and deployment
   gates are pending. No scheduled workflow has been enabled.

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
- A main-only GitHub environment restricts signing. Daily deployment also requires
  main; controlled manual previews use the existing repository deployment secret.
- All publication paths share a non-cancelling concurrency group.
- Build and verify before deploying; persist a prepared state before deployment,
  promote its validated release receipt after a successful atomic Pages upload.
  A failed run leaves the current production deployment intact and supports retry.

## Progress

1. Inspected merged PR history, root/nested instructions, v1 contracts, providers,
   crypto, static renderer, workflow, tests and existing credential configuration.
2. Reviewed GDELT, NASA, Federal Reserve, NIST, NOAA, USGS, Commons and NASA
   library rights/contracts. Publisher bodies, publisher images and YouTube API
   metadata are excluded. Verified Wikimedia's 2026 thumbnail-host migration.
3. Foundation commit `2de9427`; media compatibility/runbook commit `decd231`.
   Dedicated `daily-v1` generated explicitly, encrypted GitHub environment secret
   provisioned, and main-only deployment branch policy verified. Original local
   showcase/archive keys were not reused. No key bytes were printed or committed.
4. Public-only state branch bootstrapped at
   `194871126807ae5c8738821f5f18002701f7bb7d`. Current dataset and production are
   still the original reviewed NASA release; no pending production release.
5. Controlled real acquisition: NASA 10 recent candidates (already captured),
   Federal Reserve 1 new release, USGS 4 new event bulletins; NIST 0 recent,
   NOAA/GDELT unavailable. Five new records plus 39 retained NASA captures = 44;
   one expired NASA capture pruned. Ten initial requests plus two explicit media
   correction queries; no paid endpoints, scraping or repeated GDELT probe.
6. Candidate `1bac7a08d973c52f3844d0cd32b4ef81b14696066131197524ca1a52f13bc2a3`:
   three public-domain Commons context images and three NASA video references.
   Legacy signatures remain byte-identical. Public export contains only metadata,
   separate actual offline analyses, public keys and signed evidence.
7. Backend regression: 392 passed, 44 integration-dependent skips. Ruff, formatting,
   mypy, schema synchronization and secret guard passed. First complete real-site
   acceptance: 54 routes at 1440/390px, all 44 record signatures, release signature,
   nine tampering/unavailable-file cases, search, topic navigation, analytics and
   image fallback passed. Zero browser errors. Further recovery cases and actual
   preview deployment checks are in progress.
8. Cloudflare's full token-list read was rejected by automatic approval review
   because an unrelated token was present. A narrowly scoped Aegis row read
   confirmed its Pages Write scope and public token ID, without retrieving its
   value. The token remains in the existing encrypted repository secret.
9. Schedule activation variable remains unset/disabled. Final default-branch
   integration and explicit owner-approved activation are still required.
10. Opened follow-up draft PR #3. First GitHub regression run found a test isolation
    issue (`GITHUB_ACTIONS` inherited by a local-credential test) and a Gitleaks
    false positive on the public Cloudflare token ID. Corrected the test without
    weakening the runtime branch guard. Added an exact-value, exact-file scanner
    exception after verifying the identifier in the dashboard URL; all other
    secret rules remain active. Full history scan now passes. The first preview
    run stopped at the test gate and did not deploy.
11. All three real Commons images loaded in Chromium; forced image failures showed
    source-link fallback. Added post-deployment verification of every audited
    public asset hash and all configured security headers, before promotion.

12. Added a signed, append-only first-capture index (20,000-entry ceiling) so
    records pruned from the 21-day view cannot re-enter as new. Reissued the
    development candidate without additional provider calls: 44 visible records,
    45 captured identities, digest
    `1906011bd28f2a6b5449104a9c794550f280bd38791efadeb08f7eea8329cedb`.
    Earlier draft candidates remain in Git history; neither was promoted.
13. Preview run `38726852469` passed data, unit and browser gates but stopped at
    the exact-expiry check. The Cloudflare date picker displays IST while the
    verification API returns UTC. The guard now compares the owner's approved
    14 January date in IST, retains active/actual-expiry checks, and logs only the
    parsed non-secret UTC expiry for verification. No credential scope or expiry
    was changed and no failed run deployed.

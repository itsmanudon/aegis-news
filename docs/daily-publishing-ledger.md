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

14. Actual preview deployed at `https://af81c963.aegis-news-showcase.pages.dev`
    (alias `https://daily-preview.aegis-news-showcase.pages.dev`). Live Chromium
    passed all 54 routes, 44 signatures, nine negative cases, three loaded images,
    search/topics/analytics and protected-route checks. The separate byte checker
    initially rejected Cloudflare's clean-URL HTML redirects; corrected it to use
    canonical routes (including the custom 404 response), then all 241 public
    inventory hashes and security headers matched. No protection was disabled.
15. Token verification confirmed actual expiry `2027-01-13T23:59:59Z`, which is
    14 January 2027 05:29:59 IST. The reviewed config now pins that exact instant,
    and runtime verification compares the exact API timestamp. This corrects the
    prior date-only documentation without changing the credential.
16. Local explicit key provisioning now refuses registered key-ID replacement,
    preserves older verification keys on versioned rotation and refuses to run
    in Actions. Focused publication tests: 61 passed.
17. Final preview publication succeeded:
    [run 38728198673](https://github.com/itsmanudon/aegis-news/actions/runs/38728198673).
    Immutable URL `https://5b06089a.aegis-news-showcase.pages.dev`, alias
    `https://daily-preview.aegis-news-showcase.pages.dev`. All live browser gates,
    241 hashed public assets and security headers passed. Build commit `fbb5142`;
    subsequent whole-term context validation does not change the public bytes.
18. Final local full backend run: **402 passed, 44 integration-dependent skips**.
    Focused publication tests: **61 passed**. Ruff/format/mypy/schema checks,
    repository secret guard and Gitleaks over 71 commits passed. Three real images
    loaded; forced failures showed fallback. No protected endpoints or unexpected
    network origins/write requests were observed.
19. Current preview export:
    `1906011bd28f2a6b5449104a9c794550f280bd38791efadeb08f7eea8329cedb`,
    updated **15 October 2026 11:27:16 UTC / 16:57:16 IST**. Anonymous production
    still has the original 40-record NASA digest `be21a984…96129f`, updated
    09:06:17 UTC. Prepared state remains null; previews did not promote production.
20. Follow-up [PR #3](https://github.com/itsmanudon/aegis-news/pull/3) contains the
    implementation and security review. Exact source-code revision `bbfd0e2`;
    final PR checks are visible on its Checks tab. No default-branch merge or
    unattended activation has been performed. All required secrets are configured;
    real main-only environment signing and production promotion await the final
    owner-approved integration step. No paid resources were created.
21. The main-only manual dispatch can execute the complete first production trial
    while the unattended activation variable remains unset. The schedule still
    requires `DAILY_PUBLICATION_ENABLED=true`; enable it only after the approved
    first run signs, deploys, verifies and promotes successfully.
22. Resumed engineering review on 21 October 2026. Fetched all current refs;
    main remains `6334cc7`, daily feature head was `4f78795`, PR #2 is merged,
    PR #3 is open and its latest backend/frontend/migration/security checks passed.
    Verified secret names and main-only environment policy without reading secret
    values. `DAILY_PUBLICATION_ENABLED` remains unset. No integration authorized.
23. Added explicit recovery for upload/live-check failure: pin and verify the
    prior production deployment before upload, restore with the Pages rollback
    API, verify its exact original inventory/headers and retain failed status.
    Bounded previous-deployment lookup supports interrupted prepared releases.
    Preview exercises checkpoint reads without changing production. Actual
    production rollback remains reserved for the approved integration trial.
24. Fixed rotation to select exactly one active reviewed daily key; retired keys
    still verify history but cannot stage/resume new publications. Same-run URL
    duplicates preserve earliest acquisition. Cards now show actual acquisition
    time, the lead attributes its publisher, and all pages use source-update
    timestamps consistently. Corrected NOAA's rights link to its reuse policy.
    Pinned credential-bearing workflow actions to verified upstream commits.
25. Focused publication/recovery suite: **75 passed**, including bounded recovery,
    no token transmission to public origins, invalid targets, changed checkpoints,
    retired/ambiguous signing keys and earliest-capture preservation. Full
    regression and a fresh controlled acquisition/preview are underway.
26. Full backend regression: **416 passed, 44 service-dependent skips** using the
    documented test CORS origin and a fresh system temporary directory. An
    inherited local CORS setting and Windows replacement restrictions under the
    repository temporary directory affected the first run; neither required a
    product change. Ruff/format/mypy/schema/secret checks passed.
27. Controlled acquisition completed at **21 October 2026 17:42:50 UTC**:
    NASA 10 recent candidates, Federal Reserve 1, NIST 1, USGS 15, GDELT 26;
    NOAA unavailable. **Nine total provider/media HTTP requests**, no paid APIs,
    no publisher-page scraping. Selected 44 new records (NASA 8, Fed 1, NIST 1,
    USGS 8, GDELT 26); 29 prior NASA captures retained and 11 pruned. Published
    candidate population: **73 records, five acquisition providers, 29 publishers**;
    three per-file public-domain Commons images and three official NASA video links.
    Export **262,464 bytes**, digest
    `4f757eca85ba0db39545f62549303b9102fa82966d30c9491f464ec94788a18e`.
    Acquisition source commit `fd8fcc0`. The seven-day catch-up window reflects
    the unactivated pipeline's gap since 15 October; this is not all today's news.
    Publication is unknown for GDELT/USGS (34 records); discovery/update times
    remain explicit. Actual baseline topics: General 66, Business 3, Company 1,
    Technology.AI 2, Politics/Public-Policy 1. No labels were forced for balance.
28. Real candidate browser acceptance: **87 routes at 1440/390px, 73 record
    signatures, complete release signature and nine negative cases passed**;
    all three images loaded, fallback/search/topics/analytics/protected-route
    checks passed, zero browser errors. Visual review found portrait thumbnails
    could expand their reserved image region; constrained the 16:10 region,
    retained full-image presentation and added a browser geometry assertion.
29. CI exposed an Actions-environment isolation omission in the new ambiguous-key
    test; explicitly setting that test's local mode preserves the runtime branch
    guard. Security audit also found `PYSEC-2026-4320` in locked certifi 2026.7.22.
    Updated only certifi to **2026.10.19**; Python production dependency audit now
    reports no known vulnerabilities. No scanner rule or security gate disabled.
30. Corrected image geometry passed the full real-site browser suite again.
    Under PR-style Actions environment variables, 55 daily/recovery tests passed;
    the complete focused publisher suite is 75 tests. Node production audit also
    reports no known vulnerabilities. Both manual/daily publishers now run
    dependency audits on every execution, so new advisories block deployment.
31. New public release staged at data-branch commit
    `39e75100ba127ecacfcbbe2e568f21459efd3c0b`. Authoritative production digest
    remains `be21a984…96129f`, with `prepared.json` null; preview staging did not
    promote the candidate. Production still has **40 signed NASA records**,
    timestamp **15 October 2026 09:06:17 UTC**.
32. **Preview publication succeeded** in
    [run 39647028765](https://github.com/itsmanudon/aegis-news/actions/runs/39647028765),
    build commit `9ba1e00`. Immutable deployment:
    `https://5a90ff84.aegis-news-showcase.pages.dev`, alias
    `https://daily-preview.aegis-news-showcase.pages.dev/`.
    Actual live Chromium passed **87 routes at desktop/mobile widths, all 73
    record signatures, release verification, nine negative cases, three loaded
    images plus forced fallback**, search/topics/analytics and protected-route
    checks, with zero browser errors. **390 deployed public asset hashes and all
    configured security headers matched** the audited build.
33. The actual deployment credential passed live ID/status/expiry and static
    destination checks. Read-only production recovery checkpoint passed too,
    verifying the original production deployment's **219 public asset hashes and
    security headers**. No rollback or production mutation was invoked. Signing
    secret name/environment restriction is present; use of that encrypted secret
    remains reserved for the approved main-only production trial.
34. **Material cost correction:** final `gh repo view` returned **PRIVATE**. Earlier
    statements that standard runners were unconditionally free for this repository
    were incorrect. Account plan/remaining minutes/paid-usage blocking are unknown:
    billing APIs returned 404 and require unavailable `user` scope; browser billing
    access is policy-blocked. Did not broaden credentials, change visibility,
    purchase anything or alter account billing. Cancelled remaining runs
    `39647958202` and `39647955252` to limit further unverified metered use.
35. On `d0bd9bc`, backend, migrations, dependency/secret/history security checks,
    and frontend unit/lint/type/build gates passed. The private frontend browser
    suite was still running when cancelled; it remains an explicit revalidation
    requirement. The separate public-preview run and all its live checks passed.
36. Added pre-run cost gates to both publishers: every publication requires
    owner attestation `ACTIONS_PAID_USAGE_DISABLED=true` of an applicable hard $0
    paid-usage budget. That variable and `DAILY_PUBLICATION_ENABLED` remain unset.
    Corrected cost/runbook/PR claims. The final commit intentionally uses a CI skip
    marker to avoid starting more metered jobs until budget confirmation; this
    does not mark cancelled/pending checks passed or remove any required gate.

## Final Private-Repository Validation — 22 October 2026

- Owner explicitly authorizes one complete hosted CI attempt and, if needed for
  an established issue, one targeted retry. This overrides the earlier hold on
  controlled CI only. No merge, publication, signing-secret access or schedule
  activation is authorized; the hard $0 publication guard remains mandatory.
- Fetched current refs. Expected/actual starting HEAD is
  `a8ff2787bdc076328f771a88287b0d40d9337701`; checkout was clean. PR #3 is open,
  non-draft and mergeable. Both cost/schedule variables are absent. Cloudflare
  secret name and dedicated signing secret name exist; signing environment's
  custom branch policy is exactly `main`. No credential/settings mutation.
- Account billing usage endpoints still return 404 and request unavailable `user`
  scope. No scope refresh was attempted. The older successful preview's timing
  endpoint reports run duration 192,000 ms and billable total 0 ms; this is only
  endpoint-reported run data, not account-wide billing or budget verification.
- Durable state remains at `39e75100ba127ecacfcbbe2e568f21459efd3c0b`, current
  digest `be21a984…96129f`, 40 records, pending state null. HTTPS production and
  signed staged/preview release match their expected digests. Preview still has
  73 records and six media references, timestamp 21 October 17:42:50 UTC.
- Local backend regression: **416 passed, 44 service-dependent skips**; Ruff,
  formatting, mypy (135 files), schema synchronization and secret guard passed.
- Added `validation_only` dispatch selection to existing CI to run all four
  required validation jobs without the private demo stack or any publication.
  Validation takes precedence over conflicting publication inputs. Preparation
  commits use a CI skip marker to prevent duplicate automatic hosted runs.
  Local frontend checks passed: **69 unit tests**, API-contract generation,
  ESLint, TypeScript and production build; complete browser suite **103 passed,
  11 existing opt-in/platform skips**. No frontend product code changed.
- Dispatched the one complete hosted attempt:
  [39656611440](https://github.com/itsmanudon/aegis-news/actions/runs/39656611440),
  exact source revision `a58514e584710c8c915b6ce9d21678b287c3da96`,
  `validation_only=true`, `public_showcase=false`, `deploy=false`. Backend,
  security and migrations passed. Private demo and publication jobs were skipped
  as designed. Frontend unit/API/lint/type/build passed, but the browser suite
  failed with three timeouts (operations visual, operations reflow, polished
  reflow), one flaky reader reflow and 99 passes/11 skips. No retry dispatched yet.
- Repeated existing-preview acceptance without deployment: **87 routes at
  1440/390px, 73 record signatures, release signature, nine negative cases,
  three loaded images/fallback, search/topics/analytics/protected-route checks**
  passed, zero browser errors. **390 asset hashes and security headers matched**.
- Reviewed source policies/strict exports, active-key selection/main-only signing,
  CAS state preparation/promotion, deployment preflight, pinned production
  recovery and failure tests. No licensing or trust-policy expansion. The
  encrypted signing secret's actual value remains unverifiable until the
  separately approved main-only trial. No actual production rollback exercised.
- Diagnosed the hosted frontend timeouts around repeated navigation/operator
  setup on the four-worker development server. Local development and production
  suites pass, so resource pressure/development compilation is an inference,
  not a proven application defect. Switched CI to the installed Next guidance's
  standalone production server, copying static/public assets into ignored output,
  and two workers. Assertions, existing timeouts/retries/skips remain unchanged.
  Added a validation-only frontend selector so the permitted targeted attempt
  cannot repeat backend/migrations/security or invoke publication/demo jobs.
- Final standalone production harness passed the complete local browser suite:
  **103 passed, 11 existing skips, zero failures/retries** (1.9 minutes), including
  all three previously failing tests. ESLint, TypeScript and production build
  passed. Protected publication workflows and trust registry are unchanged.
- The one targeted hosted retry succeeded:
  [39659031583](https://github.com/itsmanudon/aegis-news/actions/runs/39659031583),
  source `d30e7252c3e94f8e7e88dcec0ad16ec979523b39`, frontend only. API generation,
  **69 unit tests**, lint, types, production build and **103 browser tests passed**;
  11 existing opt-in/platform skips, no failures or flaky retries (browser 3.1m).
  All five other jobs were skipped. Hosted allowance used: **one complete attempt
  plus one targeted attempt**; no further dispatches or reruns authorized here.
- Full-attempt evidence: backend **416 passed / 44 service-dependent skips**;
  migration roundtrip/metadata passed, database **21 passed / 2 skips**, ingestion
  **13 passed / 3 skips**; security Redis integration **1 passed**, Python/Node
  audits no known vulnerabilities, secret guard and Git history scan passed.
  Those runtime files, tests and lockfiles are unchanged in the frontend retry.
- Observable usage: full run duration **464s**, targeted run **283s**. Executing
  job times were backend 45s, security 39s, migrations 79s, first frontend 459s,
  targeted frontend 278s: **900s summed job execution (15m)**. Both timing APIs
  report Ubuntu `total_ms=0`; this is not proof of zero charges, remaining minutes
  or a spending block. Account billing remains unavailable; no scope broadened.
- Final state revalidation again passed all current record/trust checks at
  `39e75100…3c0b`, digest `be21a984…96129f`, 40 records and null prepared state.
  Publication/schedule variables remain absent, signing environment still permits
  exactly `main`, and secret names exist. Production, preview, keys, credentials,
  default branch and environment settings were not changed.
- PR #3 has no unresolved review threads, is open/non-draft and mergeable.
  Technically ready for owner merge approval with the explicit integration gates
  in the runbook. Main-only encrypted secret signing and real production
  prepare/deploy/verify/promote remain unexercised by design; an actual rollback
  is not claimed. The final handoff commit changes documentation only and skips
  automatic CI to honor the attempt ceiling; tested code is `d30e725` (frontend)
  and `a58514e` (unchanged backend/migrations/security runtime).

## Local Manual Publisher — 23 October 2026

- PR #3 merged normally at `319c50322ecc5210be03722142b564a91ec9b9a4`;
  [main CI 39790652247](https://github.com/itsmanudon/aegis-news/actions/runs/39790652247)
  passed all four validation jobs without publication. All 18 feature commits
  remain reachable; production's 40-record dataset/manifest and preview's
  73-record dataset/manifest were unchanged after integration.
- New work starts from that current main in a fresh task checkout on
  `feat/local-publication`, preserving the original checkout. This execution host
  is Windows; macOS compatibility is implemented but actual Mac credential or
  execution checks cannot be claimed.
- Added `public_showcase local-publish --dry-run|--publish|--status`, reusing
  existing acquisition, offline processing, signer, export, static/browser gates,
  state prepare/promote and Pages recovery. Extracted existing successor checks
  into a read-only shared method so dry runs/resumption enforce them too.
- Explicit publication uses a create-only coordination tag with a unique
  public-data commit, local process lock, current source/state checks, pinned
  rollback and post-upload live verification. No lock stealing/expiry. Failed
  recovery or uncertain upload timeout retains the lease for owner inspection;
  failure never erases pending release evidence. The public dataset format,
  all three protected workflows and trust registry are unchanged. Subsequent
  dependency-lock changes below remediate newly reported audit advisories.
- Local GitHub identity/permissions and disabled hosted controls were checked.
  The existing ignored `daily-v1` file in the original checkout matches the
  active reviewed public key; it was read in place, never copied or printed.
  No Cloudflare token/account/project variables are supplied to this runtime.
  No Doppler configuration was guessed or Actions secret retrieval attempted.
  A production publication cannot proceed without the reviewed Cloudflare token.
- Local backend regression passed **438 tests / 44 service-dependent skips**
  before the final seven checkout/Actions guard cases were added. The focused
  publication/recovery suite passed 103 cases before the final Actions-only guard;
  Ruff, mypy (136 files), schema synchronization and secret guard passed.
  Actual dry-run acquisition/browser results are recorded after execution below.
  No hosted runner, publication dispatch or schedule activation is authorized
  or required by this local command.
- The controlled dry run captured 28 recent permitted records in 10 provider/media
  attempts and selected 18: NASA 8, USGS 8, Federal Reserve 1, NIST 1. GDELT and
  NOAA were unavailable; no additional probe was attempted. The signed candidate
  has 43 visible records (33 NASA, 8 USGS, 1 Federal Reserve, 1 NIST), four
  publishers, three Commons images and three NASA video references. Retention
  removed 15 older visible rows while preserving their first-capture index.
- Initial dry-run gates correctly stopped at a newly reported Python advisory,
  `CVE-2026-114603` / [GHSA-xcq7-p3pf-p88h](https://github.com/advisories/GHSA-xcq7-p3pf-p88h).
  Patched API/SDK to 1.45.1 and matching constrained instrumentation packages to
  0.66b1; no broad lock upgrade or advisory suppression. Python audit is clean.
  Node audit also reported three Next.js advisories, including two critical
  ([SVG](https://github.com/advisories/GHSA-2464-fhr4-w9xw),
  [cache](https://github.com/advisories/GHSA-673q-mjm6-r5xr)) and one high
  ([Server Actions](https://github.com/advisories/GHSA-p3m5-59mp-jv5r)). Raised
  Next/eslint-config-next minimum to 16.4.1 with matching locked dependencies;
  Node production audit is now clean. These required audit fixes change the
  dependency locks; protected workflows and trust/credential files stay unchanged.
- Added dry-run-only `--recheck <run-id>` to finish validation of the preserved
  exact signed capture without more source requests. It cannot publish, use an
  arbitrary path or override a pending remote release. Original failed evidence
  remains intact. On the Python security patch, full local backend regression
  passed **450 / 44 service-dependent skips**, including the recheck cases.
- Next 16.4.1 passed API, 69 unit tests, lint, types and production build. Its first
  browser run exposed an existing pagination assertion race: the test applied a
  strict single-element text assertion while two previous-page rows still
  rendered during transition. Added an explicit one-row page-count assertion
  before the original checks. No product UI, original assertion or timeout was
  removed. The complete local browser suite is being revalidated; no hosted run.
- The corrected complete Next browser suite passed **103 / 11 existing skips**
  without failures or flaky retries (1.7m). No product frontend behavior changed.
- Final actual local recheck succeeded at code revision `0aa3a720…6827`, using
  the exact original capture from `745e93d8…f572` without new provider requests.
  Both dependency audits, 109 focused publication/recovery/coordinator tests,
  secret guard and static/browser gates passed. **239 allowlisted files, 54
  routes at 1440/390px, all 43 signatures, nine negative cases, all three loaded
  images/fallback, search/topics/analytics and protected-route checks passed**;
  zero browser errors. Generated release digest:
  `4a9d0feb3c5b4955c9f09a760acdfff91def4ce7e343e868481ed6522893743c`.
  The original failed receipt remains preserved; success did not rewrite it.
  Successful local receipt:
  `.data/local-publication/runs/20261023T102636Z-2bdf67d9d8ec4a94aad2654967d62faa/receipt.json`.
- **No actual production publication attempted:** the reviewed Cloudflare token
  is not injected into this runtime (account/project variables also absent).
  These are prerequisites, not permission to retrieve encrypted Actions secrets,
  use a different identity/token, rotate keys or relax verification. This host
  remains Windows; the Mac session/credential setup requires verification there.
  The default ignored key path in the fresh clone is not populated; actual dry
  checks read the matching existing key in place through explicit `--key-file`.
  Live deployment/rollback and distributed-lock creation are mocked, not claimed
  as executed against production. The owner-authorized production condition was
  unmet, so `--publish` was never invoked.

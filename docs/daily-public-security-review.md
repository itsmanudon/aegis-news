# Daily Publisher Security Review

This is an implementation security review and executable acceptance record,
not an independent certification or a formal Codex Security scan.

## Scope

Reviewed the acquisition/source policies, v1/v2 public contracts, offline
processing adapter, dedicated signer, static renderer/browser verifier,
public-state Git operations, deployment preflight/byte verifier, CLI/coordinator,
manual and scheduled workflows, public trust/configuration files and tests.
Existing private API authentication, archive encryption, Temporal and the local
application were not changed by this extension.

## Boundaries And Checks

- Requests use eight fixed approved endpoint URLs (six news providers, two media
  APIs). No discovered publisher, thumbnail or article URL becomes a server-side
  fetch destination. Redirects, unsafe URLs, XML entity/doctype declarations,
  oversized responses and unsupported source identities fail closed.
- External strings are data: normalized/bounded fields, escaped HTML and
  structured GitHub API JSON. No headline, publisher or media text becomes shell
  code. The offline keyword/lexicon engine does not execute news instructions.
- Strict exports reject extra fields, bodies/private archives, incomplete model
  evidence, unknown/revoked keys, changed content, broken lineage and invalid
  release signatures. Legacy bootstrap membership is pinned to its reviewed
  digest. V2 binds record membership, first-capture history, media associations,
  source commit, sequence and parent digest.
- Media requires explicit item-level reuse conditions and matching license URL.
  Matching uses whole headline terms: "Marshall" cannot silently match "Mars".
  Only explicit Commons CDN image hosts enter CSP. Videos remain external NASA
  references. No YouTube metadata, publisher thumbnails or downloaded video bytes
  enter permanent Git state. Missing media is visible and image errors have a
  source-link fallback.
- Static output is reconstructed from a strict inventory and byte-compared before
  publication. Extra files, links to missing routes, forms, frames, inline handlers,
  protected/local endpoints, credential persistence and detected secrets are
  rejected. Explicit export/file/count/total-size ceilings remain below Pages Free
  limits. The deployed preview's 241 hashed public assets and all configured
  security headers were also checked over anonymous HTTPS.
- Browser acceptance verifies every record's exact published metadata/analysis
  bytes, Ed25519 signature and complete lineage, plus the whole-release envelope.
  It rejects metadata/analysis/signature/lineage/key/registry/release substitutions
  and unavailable evidence. A signature is not factual accuracy or authentication
  of external media bytes. Separately trusted registry comparison remains necessary
  to identify the signer independently of the hosting origin.
- State is public-only. Writes use a fixed repository/branch, allowlisted paths,
  exact prior head and non-forcing updates. The first-capture index is append-only,
  so pruning cannot reset identity or original acquisition. A prepared release is
  durable before deployment; promotion requires its live manifest. Failure and
  restart tests cover stale heads, wrong parents, pending-release resumption,
  failed deployment, successful promotion and state/live rollback mismatch.
- Scheduled signing requires the expected repository and main ref; its encrypted
  secret is in a main-only GitHub environment. Key provisioning refuses Actions,
  existing key-ID replacement and writes outside ignored local `.keys`. Explicit
  versioned rotation retains older public verification keys. No original showcase
  private key or archive key was migrated.
- Deployment verifies the known account-owned credential ID, active status and
  exact expiry, fixed Pages project, Direct Upload mode, production branch and
  absence of runtime bindings/environment variables. It creates no cloud resource
  or paid plan. The scheduled workflow is gated until approved integration and
  explicit activation. Manual previews do not promote production state.
- No PR-triggered workflow receives signing/deployment secrets. Checkout does not
  persist credentials in publication jobs. The daily job needs repository
  contents-write for state; its code uses that permission only on the fixed data
  branch. GitHub's built-in token permission itself is not path/branch-scoped.

## Measured Validation

See the execution ledger for exact commits, CI and deployment run links.
Focused public tests passed (61 cases); the real 44-record, six-media export
passed all 54 routes at 1440/390px, all 44 record signatures, whole-release
verification and nine browser tampering/unavailable-file cases. All three real
Commons images loaded, forced loading failure showed fallback, search/topics and
analytics matched the actual population, and protected-looking routes returned
404. No browser write request or unexpected network origin was observed.

Ruff, formatting, mypy, schema synchronization, repository secret guard and
Gitleaks history scanning passed. Gitleaks initially flagged the public
Cloudflare token ID; its exception is constrained to that exact non-secret value
in `apps/showcase/deployment.json`. No path-wide or general token exemption was
added. Private backend/frontend/migration/security CI remains required on the PR.

## Practical Limits

The minimally scoped Cloudflare credential cannot read token permission policies.
Its Pages Write scope/account were inspected in the dashboard and pinned as a
reviewed attestation; live identity/status/expiry are checked automatically.
Any scope change requires owner review. Trusted-main or deployment-account
compromise remains outside the protections of browser signature consistency.

Real production promotion and unattended environment signing can only be exercised
after the final approved main integration. Preview deployment, actual live bytes,
local dedicated signing and success/failure state transitions have been tested;
they do not claim that an unactivated daily workflow has already run in production.
GitHub scheduling, free news APIs and external media availability have no promised
delivery SLA. Provider outages and English-language discovery limit coverage. Immutable public Git
history cannot support sources that require deletion of retained metadata.

## 21 October Revalidation

GDELT recovered in a single controlled nine-request provider/media run: the new
candidate has 73 records from five acquisition providers and 29 publisher names,
with three per-file public-domain images and three external NASA video references.
Full local backend regression: 416 passed / 44 service-dependent skips. Focused
public boundary/recovery suite: 75 passed. Real candidate browser verification:
87 routes, 73 signed records and nine negative cases; three images loaded.

Added a pre-upload checkpoint of the previous validated static production
deployment and its original public inventory/headers. Failed upload/live gates
invoke the Pages rollback API and verify the restored bytes, with three bounded
verification attempts. Preview exercises checkpoint reads without production
mutation. Mocked transport tests cover recovery, missing/modified targets, no
bearer transmission to public origins, bounded lookup and unsuccessful recovery.
An actual production rollback is not claimed; hard runner termination can prevent
cleanup and requires the documented owner recovery action.

Signing now selects exactly one active daily key from reviewed trust, and refuses
new publication with retired keys while retaining historical verification.
Credential-bearing actions are pinned to upstream commits. CI's newly reported
certifi advisory was remediated through a targeted lockfile upgrade; Python audit
passed with no known vulnerabilities. No existing security check was relaxed.

Successful live preview run:
[39647028765](https://github.com/itsmanudon/aegis-news/actions/runs/39647028765),
immutable deployment `https://5a90ff84.aegis-news-showcase.pages.dev`.
All 390 preview asset hashes/security headers matched, and live browser checks
passed all 87 routes/73 signatures/nine negative cases. The real, read-only
rollback checkpoint also verified the prior production deployment's 219 public
asset hashes and headers. Actual credential identity/status/expiry checks passed.
Neither a production rollback nor unattended signing activation was performed.

Final repository-visibility check returned **PRIVATE**, contradicting the earlier
public-repository cost assumption. Billing API access requires scope unavailable
to the current credential; browser billing access is policy-blocked. Remaining
CI was cancelled to limit unverified metered use. Backend, migrations, security,
and frontend unit/lint/type/build checks passed on `d0bd9bc`; its private frontend
browser suite was interrupted and is not claimed as passed. Static preview
acceptance above completed successfully before this discovery.

Both publication jobs now require owner attestation
`ACTIONS_PAID_USAGE_DISABLED=true` before runner allocation. Missing attestation
does not grant access. This is a fail-closed owner-attested cost boundary, not a
live billing guarantee. No secret scope was broadened, repository made public or
paid plan purchased. Owner budget confirmation and final hosted revalidation
remain required. The cost-gate commit intentionally skips hosted CI to avoid
additional potentially billable work; existing checks have not been disabled.

# Public Showcase

## Daily Extension Status

PR #2 was merged by the owner on 15 October 2026 at
`6334cc7e213744b0d787a27556e8a74232e32884` (main CI passed). The follow-up branch
`feat/daily-publication` extends this publisher with bounded free multi-source
acquisition, licensed context images, NASA video references, a versioned daily
signing key and durable public-only Git state. See the
[daily runbook](daily-publishing.md), [execution ledger](daily-publishing-ledger.md)
and [security review](daily-public-security-review.md).

The original manual-only policy below describes the PR #2 release. The owner's
new daily-publishing assignment supersedes it for the extension. The new schedule
is **06:23 UTC / 11:53 IST**, but remains gated until approved default-branch
integration and explicit `DAILY_PUBLICATION_ENABLED=true`. No automatic merge or
schedule activation is performed during feature development. Production remains
the original validated NASA release. The new release is publicly accessible at
[the daily preview](https://daily-preview.aegis-news-showcase.pages.dev/) and has
passed anonymous browser and static-byte checks.

Successful preview workflow:
[38728198673](https://github.com/itsmanudon/aegis-news/actions/runs/38728198673).
Immutable preview: `https://5b06089a.aegis-news-showcase.pages.dev`.
Export `1906011bd28f2a6b5449104a9c794550f280bd38791efadeb08f7eea8329cedb`,
updated 15 October 2026 11:27:16 UTC / 16:57:16 IST. Follow-up:
[PR #3](https://github.com/itsmanudon/aegis-news/pull/3).

The controlled candidate contains 44 genuine records: 39 retained NASA captures,
one new Federal Reserve Board release and four new USGS event bulletins. It adds
three per-file public-domain Commons context images and three official NASA video
references. GDELT and NOAA were unavailable; NIST had zero records in the recent
window. These limitations are reported without invented coverage or publication
dates. Expected incremental hosting/provider cost remains **USD $0/month**.

## Original PR #2 Release

## Delivery

Feature branch: `feat/public-showcase`, based on validated main
`fd4eb0254d8f4d36398b5575aa3cbb6effab3958` (successful main CI run
[`38298752612`](https://github.com/itsmanudon/aegis-news/actions/runs/38298752612)).
Implementation commit: `ea52f4c` (the frozen export identifies the full SHA).
The feature branch is not merged automatically.

Frozen export SHA-256:
`be21a98429a1a44cd83ad7b74c5a00e558e0318780c08935572588a89396129f`.

Public production hostname: `https://aegis-news-showcase.pages.dev`.
Deployed successfully on 15 October 2026 through the manual GitHub Actions entry
point: [publication run 38712273910](https://github.com/itsmanudon/aegis-news/actions/runs/38712273910).
Immutable deployment URL: `https://00376410.aegis-news-showcase.pages.dev`.
Deployment build commit: `ab44975` (subsequent handoff/test-script changes do not
change the published export or static application).

Anonymous HTTP and browser checks passed against production. The public manifest
matches the local audited release; all 219 public assets referenced by its file
inventory match SHA-256 byte-for-byte (`_headers` is Cloudflare configuration, not
a served asset). Root returns 200 without authentication or cookies. Security
headers are active; private-looking routes return 404. All 50 pages passed at
desktop/mobile widths, all 40 signed records verified, and six negative evidence
cases failed closed on the live site. No unrelated cloud resource was created.

## Architecture Decision

The existing Next.js app depends on authenticated API adapters, mutable operational
pages, development identity and runtime document routes. Adapting it would require
maintaining a second authorization and route configuration inside the private app.
Instead, `apps/showcase` is an independent static HTML/CSS/JavaScript application
with a small Python renderer. It shares the actual Inter and Source Serif 4 font
assets and Paper `#f7f6f2`, Ink `#17212f`, Teal `#0f766e` tokens.
There is no new frontend framework or production runtime dependency.

The public bundle does not import private frontend components. No local API route,
authentication setting, Temporal workflow, archive, database or security demo is
changed. Private processing uses existing `Article`, `IngestionRequest`,
normalization, offline intelligence adapters, `StandardCryptoProvider` and
`ProvenanceService` contracts, with a separate publication signing key.
The local curated metadata file under ignored `.data/showcase` is the publication
input; this exporter intentionally does not dump the private application's database.

```text
Explicit Local Collection → Local Contract Validation & Offline Processing
→ Curator-Reviewed Signed Export → Validate Exact Export Digest
→ Build & Audit Static Files → Browser Checks → Manual Pages Direct Upload
```

Publication needs no provider key, private API, signing key, database, Redis,
Temporal, ML weights or inference service. The GitHub runner validates existing
signed bytes and builds files; it does not collect news or process models.

## Cost Configuration

Expected incremental cloud cost: **USD $0/month** for this configuration.

| Item | Configuration | Expected Monthly Charge |
| --- | --- | --- |
| Cloudflare Pages | Free, static files, `pages.dev` hostname | $0 |
| Pages Functions / Workers | None deployed | $0 |
| R2, KV, D1, hosted compute, databases | None created | $0 |
| News acquisition | Manually requested official NASA metadata, no API key | $0 |
| GitHub Actions | Public repository, standard `ubuntu-latest` runner, manual publication | $0 |
| Custom domain | None purchased or configured | $0 |

Cloudflare documents unlimited static requests and bandwidth on Pages Free,
500 platform builds/month, one concurrent build, 20,000 files/site and 25 MiB/file.
Direct Upload builds locally or on GitHub, avoiding a Cloudflare build service.
The initial output is 221 files, about 1.03 MiB zipped; no asset approaches 25 MiB.
The workflow uploads no retained GitHub artifacts and enables no paid services.
Local electricity and existing unrelated account resources are outside this estimate.
If limits change or are exceeded, stop and review; do not upgrade automatically.

References, checked 15 October 2026:
[Cloudflare Pages Pricing](https://www.cloudflare.com/developer-platform/products/pages/),
[Pages Limits](https://developers.cloudflare.com/pages/platform/limits/),
[Direct Upload With CI](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/),
[GitHub Actions Billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Sources, Rights And Corpus

The initial frozen corpus contains **40 genuine NASA metadata records**:
10 entries from `https://www.nasa.gov/feed/` and 30 press releases returned by
NASA's public WordPress press-release endpoint in the explicitly requested window
15 September–14 October 2026. Actual returned publication dates span
23 September–15 October 2026. Acquisition timestamps are captured when records are
parsed; publication dates are taken from RSS `pubDate` or WordPress `date_gmt`.
Canonical URL hashes deduplicate source identities across feed and backfill.
Duplicate refreshes preserve the original acquisition timestamp and headline.

The public policy `nasa-metadata-only-v1` publishes only the headline, canonical
source link, publisher attribution, publication/acquisition timestamps, and Aegis
analysis/provenance of those public bytes. No publisher excerpts, article bodies,
image/video assets, NASA marks, raw feed responses or third-party material are
republished. Original pages remain the place to read reporting and inspect media.
NASA affiliation or endorsement is not claimed.

Review [NASA Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)
when changing the policy. NASA pages can contain separately copyrighted third-party
material. This metadata-only export asserts no blanket rights over that material.
No provider-imposed metadata storage expiry is identified for these official NASA
interfaces. If a future source imposes an expiry, it must not be added to this
indefinitely frozen contract without an explicit removal/republication procedure.
Paid/commercial news providers and YouTube are excluded from this public policy.
An initial free GDELT availability probe returned 429; no GDELT records are published.
The separate NASA Science RSS endpoint returned malformed XML and was excluded.

All 40 initial headlines classify as `general` under Aegis's existing taxonomy.
The site says so rather than inventing science categories. Entity candidates are
capitalized spans, unresolved and unreviewed. Event candidates can be absent.
Sentiment is a lexicon baseline. These are actual Aegis offline model outputs,
not generative summaries, trained-model inference, publisher labels or verified facts.

## Public Routes

| Route | Supported Experience |
| --- | --- |
| `/` | Discover and evidence trail |
| `/archive/` | All records; browser-only headline search and topic filter |
| `/stories/<sha256>/` | Attributed source record, timestamps, model receipts and verification |
| `/topics/`, `/topics/<label>/` | Existing headline topic assignments and linked records |
| `/evidence/` | Entity span and event candidate evidence linked to source records |
| `/analytics/` | Corpus-only topic/sentiment counts and honest denominators |
| `/media/` | Original source links and explanation that no media is published |
| `/verification/` | Actual crypto design and browser verification |
| `/about/` | Sources, rights and limitations |
| `/404.html` | Explicit missing-route page, preventing SPA fallback into protected-looking routes |
| `/data/manifest.json` | Deterministic release identity, per-file hashes and source commit |
| `/data/dataset.json` | Only the validated public contract |
| `/data/evidence/<sha256>/...` | Exact metadata, analysis, signed manifest and signed-body bytes |

There are 49 content routes plus the custom 404 page in the initial release.
No public operational forms, ingestion/provider controls, identity selector,
token form, administrator persona, private audit or write endpoint is included.

## Manual Refresh

Run from the repository root. Nothing here has a schedule, polling loop or
automatic API refresh. The `collect` command is the only network acquisition step.

```powershell
uv sync --frozen --python 3.12
uv run python -m scripts.public_showcase collect --source nasa --limit 20
```

Optional one-time historical backfill (choose an explicit past window):

```powershell
uv run python -m scripts.public_showcase collect --source nasa --limit 30 --after 2026-09-15T00:00:00+00:00 --before 2026-10-14T00:00:00+00:00
```

Backfill is limited to one request, at most 100 records and a positive window of
at most 31 days. That is an Aegis safety bound, not a claim about a commercial
provider's historical entitlement. Only NASA's free public press-release endpoint
supports this command's backfill mode. No retries or pagination cause extra
acquisition requests. Current RSS feeds may contain fewer records than `--limit`.
Malformed responses, unsafe links, future acquisition times and empty results fail.

The collection is stored at `.data/showcase/collection.json` and is ignored by Git.
Review the returned records and retain at most 100 deliberately curated records.
To prepare a fresh bounded release instead of accumulating records, choose a new
`--collection .data/showcase/classroom.json` path for both collection and export.
This preserves prior local collections.

Commit exporter-code changes before preparing the final export, so its
`source_commit` identifies the processing implementation. Then:

```powershell
uv run python -m scripts.public_showcase export
uv run python -m scripts.public_showcase validate
uv run python -m scripts.public_showcase build
uv run python -m scripts.public_showcase audit
uv run pytest -q tests/unit/test_public_showcase.py
pnpm install --frozen-lockfile
pnpm --filter @aegisnews/web exec playwright install chromium
node apps/showcase/check-browser.mjs
uv run python scripts/scan_secrets.py
```

The private export key is generated once in `.keys/public-showcase`, ignored by
Git, using the existing local key provider. Keep it private and back it up safely.
The generated AES key in that private key directory belongs to the existing key
provider format; the public export process neither uses nor publishes it.
`apps/showcase/trust.json` pins only the public Ed25519 key. A new machine needs
the existing private export key for signing, or a deliberate reviewed key rotation;
it can build an existing export without any private key.

Review and commit only the approved `apps/showcase/dataset.json` changes. Do not
commit `.data`, `.keys`, generated `dist`, caches, screenshots or test results.
The canonical export SHA-256 from `validate` is the manual publication approval
identifier. Rebuilding a frozen export produces identical static bytes. Re-running
`export` intentionally produces a new release with new processing/provenance times.

To repeat the browser acceptance suite against the deployed public edition:

```powershell
$env:AEGIS_PUBLIC_BASE_URL = 'https://aegis-news-showcase.pages.dev'
node apps/showcase/check-browser.mjs
Remove-Item Env:AEGIS_PUBLIC_BASE_URL
```

That is one explicit test run; it adds no recurring requests or scheduled jobs.

## Manual GitHub Actions Publication

Workflow: [Publish Public Showcase](https://github.com/itsmanudon/aegis-news/actions/workflows/public-showcase.yaml).
Source: [public-showcase.yaml](../.github/workflows/public-showcase.yaml).
Publication is triggered by `workflow_dispatch`, either directly or through the
existing registered CI workflow's explicit `public_showcase` option and a local
reusable `workflow_call`. There is no cron, push deployment or provider call.
`deploy` defaults to false. The exact approved export SHA-256 is mandatory, and
invalid, unsigned, incomplete, duplicated or unexpectedly extended exports fail.

Repository configuration:

- Secret `CLOUDFLARE_API_TOKEN`: configured. The owner-approved account-owned token
  “Aegis News Pages Publication” grants only **Pages Write** on this account,
  expiring **14 January 2027**. Cloudflare scopes this permission to the account's
  Pages projects, not one individual project. It was transferred directly into
  GitHub's encrypted secret form; it was not printed or committed.
- Variable `CLOUDFLARE_ACCOUNT_ID`: `3de5bfe983584a2eab1cbb710aa4fbe8`.
- Variable `CLOUDFLARE_PAGES_PROJECT`: `aegis-news-showcase`.

The project is a Pages **Direct Upload** project. It has no Git integration,
automatic deployments, build hooks, Functions or storage bindings.
The workflow uses pinned Wrangler `4.151.0` only to upload audited static files.
It cannot create paid infrastructure and does not request any plan change.

GitHub requires a newly added dispatch workflow to exist on the default branch
before exposing its Run Workflow control. The existing registered `ci.yaml` provides
a manual entry point on this feature branch without merging main. Its
`public_showcase=true` mode skips every private-stack job and calls only the static
publication workflow:

```powershell
gh workflow run ci.yaml --ref feat/public-showcase -f public_showcase=true -f export_sha256=REPLACE_WITH_VALIDATED_SHA256 -f deploy=true
```

After the owner's reviewed merge, the dedicated workflow can also be dispatched
directly. This task does not merge main:

```powershell
gh workflow run public-showcase.yaml --ref main -f export_sha256=REPLACE_WITH_VALIDATED_SHA256 -f deploy=true
```

The workflow reruns contract, signature, output, secret and production-browser
checks before the upload. It publishes the already prepared dataset and never
needs the full private stack. Initial publication can use the signed-in Pages
dashboard and a ZIP containing only the audited `apps/showcase/dist` contents.

## Cryptographic Scope

`aegis/security/crypto.py` uses standard SHA-256, AES-256-GCM and Ed25519.
`aegis/provenance/service.py` signs canonical JSON and binds lineage using chained
SHA-256 values. Each public record signs canonical metadata as the raw publication
input plus canonical public analysis bytes as its dependent lineage record.
This is genuine new public publication provenance, not a claim that a private
archive's complete provenance or original publisher page has been exported.

The browser fetches the exact signed-body and content bytes, verifies Ed25519 with
Web Crypto, checks every content hash, validates input lineage and recomputes the
chain hashes. It also checks the fetched public key against the release's HTML
trust anchor. Unsupported crypto reports verification unavailable. A key served
by the same website is not independent identity proof: compare its fingerprint
with the reviewed repository or a separately trusted copy.

AES-256-GCM archive encryption (32-byte keys, 96-bit nonces, authenticated algorithm/
key/version/context header and durable nonce allocator), role/scope access control,
allowlisted/redacted security audit and complete tamper/restoration operations stay
in the private application. The public site explains their actual implementations.
No private signing/decryption keys, protected plaintext or internal audit records
are exported. **Signature validity never establishes factual accuracy.**

## Quality And Security Review

The publication contract forbids unexpected fields at every exported boundary,
allows only explicit NASA hosts and metadata policy, rejects duplicate identities
and JSON keys, requires topic/sentiment outputs, validates public headline evidence,
pins models and public keys, checks timestamps and validates every signature/hash.
The renderer HTML-escapes source strings. Search uses DOM properties, not HTML
insertion. The CSP permits only same-origin scripts, styles, fonts and static
verification fetches; forms, frames, objects and remote connections are blocked.

The output audit regenerates the entire expected inventory and compares every
byte. Extra files, symlinks, altered assets, missing routes, unsupported references,
private endpoints, credential storage APIs, known secret formats and Free-tier
asset-limit violations fail. No Functions entry point, Worker, server bundle,
source map, raw archive or database is in the allowlisted inventory.

Initial checks:

- 20 public-boundary tests passed, including tampering, key substitution, forbidden
  fields, unsafe source URLs, duplicate records/JSON, deduplication and extra files.
- 361 backend tests passed; 44 integration-dependent tests skipped. The first local
  run exposed an existing `.env` CORS-origin difference; rerunning with the expected
  origin in the test process passed. Local `.env` and authentication were unchanged.
- Existing frontend: 69 tests passed; ESLint, API contract generation check,
  TypeScript and Next.js production build passed.
- Existing frontend browser suite: 103 passed, 11 live-stack-dependent tests skipped.
- Repository Ruff formatting/lint, mypy (125 source files), secret guard and schema
  consistency checks passed.
- All 49 content routes and the custom 404 page tested at 1440px and 390px; no document overflow, forms,
  external requests or JavaScript errors. Screenshots inspected on desktop/mobile.
- All 40 browser signatures/content chains passed; changed metadata, analysis,
  manifest, signed-body and public-key bytes were rejected; missing evidence failed closed.
  Search empty state, topic filters,
  protected-route absence and analytics totals passed.

Integration-dependent Docker/Temporal/database tests are not claimed as run.
The generated-file review is scoped to this static publication; it is not a new
repository-wide security certification. No paid services, provider calls or
scheduled background jobs are introduced by the publication workflow.

## Outstanding Limitations

The corpus is deliberately narrow (NASA, headline metadata, one current general
topic). It has no full-text search, generative summaries, trained inference,
resolved entity identities, independently checked events or media authenticity
verification. Those require additional approved data and processing, not simulated
public controls. Browser verification requires modern Web Crypto Ed25519 support.
The dedicated workflow appears in GitHub's default-branch workflow list after the
owner's reviewed merge. Until then, use the existing CI workflow's explicit manual
publication option. Rotate the deployment token in GitHub before 14 January 2027.

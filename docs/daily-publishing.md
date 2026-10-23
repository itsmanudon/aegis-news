# Daily Public Publishing Runbook

## Activation Status

PR #3 was merged into `main` at `319c50322ecc5210be03722142b564a91ec9b9a4`;
all four main CI jobs passed. Production remains the validated NASA release until
an explicit publication succeeds. The **local** path below uses this computer,
not GitHub Actions, and requires neither hosted-usage attestation nor activation.
The existing **GitHub Actions** publication workflow remains gated by all of:

1. Reviewed integration into default branch `main`.
2. For unattended runs, repository variable `DAILY_PUBLICATION_ENABLED=true`
   (unset means disabled). Explicit main-branch manual dispatch can perform the
   initial complete production trial while unattended execution stays disabled.
3. Environment `public-daily-publication`, custom deployment branch policy `main`.
4. Matching encrypted environment secret `AEGIS_PUBLIC_SIGNING_KEY` and reviewed
   public `apps/showcase/trust-registry.json`.
5. Existing Cloudflare credential and destination checks, followed by all data,
   licensing, cryptographic, static-output and browser gates.
6. This repository is **private**. Before either publisher allocates a runner,
   owner variable `ACTIONS_PAID_USAGE_DISABLED=true` must attest that an applicable
   hard $0 Actions spending budget blocks paid usage. Do not set it based only on
   a notification-only budget or an assumption about remaining included minutes.

Do not set the activation variable until the final integration is approved.
After approval and merge, explicitly dispatch `daily-publication.yaml --ref main`
while the variable remains unset. Confirm that run, its real environment signing,
live digest and durable promotion receipt. Only then set the variable to enable
the next scheduled execution. A failed first trial never enables the schedule.

The schedule is **06:23 UTC / 11:53 IST daily**, `23 6 * * *`. GitHub schedules
can be delayed or dropped under load; this is not an availability guarantee.
Scheduled workflows only execute from the default branch, and GitHub may disable
public-repository schedules after 60 days without repository activity.
[GitHub scheduling behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Manual Publication From macOS

Use a trusted, clean checkout containing the local-publisher implementation and
the latest `origin/main`. The command fetches `main` without merging/resetting,
requires it to be an ancestor of the current committed source, verifies the
approved GitHub origin, and refuses tracked or unignored changes. A committed
feature checkout is supported; its actual source SHA is recorded. No source
commit/push, workflow dispatch, credential rotation or paid resource creation is
performed by the command. The static site stays online when the laptop is off.

### Initial Configuration

Install Git, GitHub CLI, uv, Node.js 22+ and the repository's pinned pnpm version.
From the repository root, using an existing approved GitHub session:

```sh
gh api user --jq .login
uv sync --frozen --python 3.12
pnpm install --frozen-lockfile
pnpm --filter @aegisnews/web exec playwright install chromium
npx --yes wrangler@4.151.0 --version
```

GitHub requires repository push permission for public-data commits/ref updates,
and read access to Actions runs, repository/environment variables and metadata.
The command verifies these using the selected `gh` identity and never requests
broader scopes or starts a hosted runner. Configure access separately if missing.
Run from the repository root, not `apps/showcase` or another directory.

### Secure Credentials

The existing matching `daily-v1` key belongs at
`.keys/daily-publication/daily-v1.key`, which is ignored by Git. It is base64 of
the existing 32-byte Ed25519 private key. Restore that exact key from an approved
secure backup if needed; do not overwrite an existing file. Restrict the private
directory to the owner and the key file to mode 600 on macOS. Never invoke
`daily-key` to solve a missing credential: the registered ID cannot be replaced.
An existing ignored key elsewhere can be read with `--key-file <existing-path>`;
no copy is made. Alternatively inject `AEGIS_PUBLIC_SIGNING_KEY` at runtime.
Its public key must match the single active reviewed registry entry; wrong or
missing keys stop before acquisition. Keys present only as Actions encrypted
secrets cannot be read back: obtain the original matching backup, or stop for a
separately reviewed rotation outside this procedure.

For **publication**, inject the existing reviewed `CLOUDFLARE_API_TOKEN` through
an approved local password manager/runtime secret mechanism, and set the public
destination values from `apps/showcase/deployment.json`:

```sh
export CLOUDFLARE_ACCOUNT_ID=3de5bfe983584a2eab1cbb710aa4fbe8
export CLOUDFLARE_PAGES_PROJECT=aegis-news-showcase
```

Do not type token/key values into shell history, print them, store them in tracked
files, or expose them in screenshots. If using Doppler, first explicitly verify
the Aegis publication project/configuration; no project is guessed or private
application/archive-encryption configuration imported. No automatic credential
discovery or fallback to Wrangler OAuth is used. The same reviewed account-owned
Pages token must pass live ID/status/expiry and static Direct Upload checks.
Its reviewed scope is account-wide Pages Write, not a single-project token; live
scope introspection is unavailable without broader permissions, so the existing
reviewed attestation is retained. Expiry remains **14 January 2027 05:29:59 IST**.

### Dry Run And Repeated Publication

```sh
uv run python -m scripts.public_showcase local-publish --status
uv run python -m scripts.public_showcase local-publish --dry-run
uv run python -m scripts.public_showcase local-publish --publish
```

Modes are mutually exclusive; one must be supplied. `--publish` is the explicit
production mutation switch. Normal repeat publication uses exactly that same
command. A dry run needs the signing credential but not Cloudflare credentials;
it reads GitHub state and the live parent, collects approved bounded news,
deduplicates and processes it, signs using the existing implementation, checks
the same parent/sequence/first-capture contracts, runs publisher/recovery tests,
dependency/secret audits, builds/audits the static output and runs desktop/mobile
browser verification. It never prepares, promotes, locks or deploys remotely.
It reports counts, publisher diversity, image/video counts, source failures,
additions/removals and release digest. Publication readiness is not inferred from
a dry run with a missing Cloudflare token.

If a local audit/browser gate fails, preserve its candidate and failed receipt.
After fixing and committing the cause, recheck that captured edition without
repeating provider requests:

```sh
uv run python -m scripts.public_showcase local-publish --dry-run --recheck <original-run-id>
```

This accepts only an ID under local run storage, revalidates the current parent,
sequence, trust and first-capture history, and produces a fresh receipt while
preserving the original failure and original candidate source SHA. It does not
claim new acquisition. It cannot be combined with `--publish` or `--status`, and
cannot supersede remote pending state. Normal `--publish` always acquires fresh
eligible news or resumes the exact remote-prepared release; it never deploys an
arbitrary cached local candidate.

Each invocation uses a fresh ignored `.data/local-publication/runs/<id>/` folder.
`receipt.json` and `.data/local-publication/latest.json` contain sanitized
status/counts/digests and failure stage; private bytes and raw subprocess output
are never saved. The candidate contains public metadata only. CLI subprocesses
use fixed argv without shell evaluation, get only their necessary credentials,
and have a ten-minute per-command timeout. The acquisition's existing request,
response-size, retry and rate limits remain unchanged. Provider failures are
reported; an empty acquisition checks the prior static edition and leaves
production/state unchanged, including its real old timestamps.

`--publish` additionally checks the reviewed destination, disabled hosted flags
and conflicting publication runs; acquires the local and remote locks; rechecks
the exact state/source head; CAS-prepares the release; pins and fully verifies the
original production rollback target; re-audits static bytes; invokes the existing
pinned Wrangler Direct Upload to `--branch main`; verifies live bytes/headers and
browser signatures; and only then CAS-promotes the durable release and confirms
`prepared.json` is null. No signing/deployment secret enters the Git state.

### Concurrency, Status And Recovery

The local `.data/local-publication/run.lock` prevents overlapping runs in one
checkout. Explicit publishing atomically creates the **coordination-only** Git
ref `refs/tags/aegis-local-publication-lock`, pointing to a unique public-data
commit. This is not a release tag, dataset, new ingestion system or signing key.
The state format remains unchanged. A second computer cannot acquire that ref;
an old process cannot remove a different owner's lock. Neither lock is silently
stolen or automatically expired. The lease commit identifies its run ID and
`lease.json` records its exact ref/SHA for recovery. Failed rollback, upload timeout or hard
interruption retains the remote lock for owner reconciliation.

Current CI ignores `publication-data` branch pushes and defines only a branch
filter, so lock tag pushes do not select CI. The other two workflows have no
push trigger. The command pins the reviewed normalized bytes of all three
workflows and refuses an inventory/trigger change until reviewed; none is edited
by this implementation. See [GitHub ref filtering](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushbranchestagsbranches-ignoretags-ignore).
Keep **both** `DAILY_PUBLICATION_ENABLED` and `ACTIONS_PAID_USAGE_DISABLED` unset.
Local publication does not need or override the hosted publication billing guard.

Inspect state without acquisition, signing or deployment:

```sh
uv run python -m scripts.public_showcase local-publish --status
gh api repos/itsmanudon/aegis-news/git/ref/tags/aegis-local-publication-lock
```

`--status` reports current/pending digests and any remote lease. HTTP 404 for the
tag means no remote lease. If a pending release exists without a retained lock,
the next `--dry-run` validates that exact signed release without new acquisition;
the next explicit `--publish` rechecks it, deploys idempotently and promotes it.
No new release supersedes pending evidence. A live candidate whose promotion was
interrupted remains pending until those checks pass. Changed parent/state,
revoked key, expired credential or a missing verified rollback target stops.

After a failed upload/live check, guarded recovery restores and byte-verifies
the pinned previous deployment; the command still fails and preserves pending
state. If recovery fails, do not retry publication. Inspect the receipt/checkpoint,
the actual live release and existing Pages rollback procedure first. A hard
interruption or timed-out upload can outlive the local command; reconcile any
in-flight upload before removing a lease, even if rollback verification passed.
Only after verifying the owning process is stopped and the exact lock SHA still
matches the inspected lease may the owner explicitly remove the coordination ref:

```sh
gh api --method DELETE repos/itsmanudon/aegis-news/git/refs/tags/aegis-local-publication-lock
```

This command is an explicit recovery action, not part of normal retry. Never
delete a release tag, alter trust, force-update `publication-data` or erase
`prepared.json`. A leftover local `run.lock` likewise needs owner inspection
before removal. Retain failed receipts and candidates for diagnosis.

### Verify The Public Website

A successful receipt requires live verification and durable promotion, not just
acquisition or upload success. Inspect the website and compare its manifest
digest with the receipt and durable state. To repeat checks against the last
locally built candidate:

```sh
AEGIS_PUBLIC_BASE_URL=https://aegis-news-showcase.pages.dev node apps/showcase/check-browser.mjs
uv run python -m scripts.verify_public_deployment --base-url https://aegis-news-showcase.pages.dev
uv run python -m scripts.public_showcase local-publish --status
```

The checks deliberately fail if the local build and live release differ. The
local development stack, authentication and archive encryption are not started
or modified. macOS execution must still be verified on the actual Mac; successful
Windows validation is not evidence of credentials installed on another device.

## Data Flow

```text
Read publication-data → Verify Signed State And Live Parent
→ Fixed Free Endpoints → Normalize / Rights / Freshness / Deduplicate
→ Publisher Round-Robin → Existing Offline Intelligence → Dedicated Ed25519 Signing
→ Validate Export → Static Build / Secret Audit / Browser Checks
→ CAS Prepare → Atomic Pages Direct Upload → Verify Live Digest → CAS Promote
```

No private API, Docker, Temporal, database, Redis, ML weights or hosted inference
is started. The public browser has no API credential or write capability.
The local private demo, access controls, AES-GCM archives and restoration remain intact.

## Provider Registry And Rights

`aegis/showcase/sources.py` is the executable endpoint/attribution allowlist.
The public site stores **headlines, publisher attribution, canonical links,
actual timestamps, available source categories and separate Aegis outputs**.
It never stores excerpts, publisher article bodies or discovered publisher images.
Publisher webpages are never fetched. Redirects from approved APIs are rejected.

| Provider | Official Endpoint | Public Fields And Rights | Auth / Quota / Freshness / Fallback |
| --- | --- | --- | --- |
| NASA | `https://www.nasa.gov/feed/` | Headline, link, feed publication date, categories; metadata and source links. [Usage guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/). Third-party content remains excluded. | No key; no fixed entitlement assumed. One request plus bounded retries; max 16 candidates. RSS freshness as supplied. Retain prior valid records if unavailable. |
| Federal Reserve Board | `https://www.federalreserve.gov/feeds/press_all.xml` | Headline/link/publication date. Public information generally public domain except marked third-party work; Board attribution. [Disclaimer](https://www.federalreserve.gov/disclaimer.htm), [RSS index](https://www.federalreserve.gov/feeds/feeds.htm). | No key; max 16 candidates, bounded retry. Press releases are intermittent, so zero recent records is legitimate. |
| NIST | `https://www.nist.gov/news-events/news/rss.xml` | Headline/link/date/categories; credit NIST, exclude copyrighted third-party content. [Copyright](https://www.nist.gov/copyrights-disclaimers), [feed index](https://www.nist.gov/coo/nist-rss-feeds). | No key; max 16 candidates. Feed may have multi-day gaps; old items are not relabelled as today's news. |
| NOAA Ocean Service | `https://oceanservice.noaa.gov/rss/nosnews.xml` | Metadata/link only with NOAA attribution, no implied endorsement. [Official feed index](https://oceanservice.noaa.gov/rss.html), [reuse policy and third-party exclusions](https://oceanservice.noaa.gov/about/faq.html). | No key; max 16 candidates. Malformed XML is rejected; no scraping or rate-limit bypass fallback. |
| USGS Earthquake Hazards Program | `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson` | Official event bulletin title/link; `time` is **event occurrence**, `updated` is **source update**, publication remains unknown. [GeoJSON contract](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php), [public-domain policy with third-party exclusions](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits). Credit USGS. | No key; max 16 recent candidates. The selected feed covers the preceding day; catch-up cannot recover older USGS events. Never fetch detail URLs. |
| GDELT DOC | `https://api.gdeltproject.org/api/v2/doc/doc` | Headline, publisher domain, canonical source link, available publisher country; `seendate` is **provider discovery**, publication unknown. [GDELT terms](https://www.gdeltproject.org/about.html#termsofuse) permit dataset use with attribution/link; do not grant publisher article/photo rights. | No key; one query max 30 results, 2–7-day window. No fixed quota is asserted. 429/5xx/network failures use three total attempts with 30/60-second backoff; long Retry-After skips provider. Other feeds continue. |

These metadata policies have no known provider-required deletion interval for
the selected fields. Recheck terms before extending fields or providers. The
21-day limit applies to the visible population; **public Git release history is
permanent**. Sources requiring deletion from immutable history must be excluded
until a different compliant state design is reviewed. No paid provider is called.

## Media Policy

One explicit headline term (Artemis, Mars or Moon) can seed two fixed API queries:

- Commons `https://commons.wikimedia.org/w/api.php`: up to three namespace-6 files
  with per-file `imageinfo` URL/extmetadata, known creator, source page and license.
  Accepted licenses: Public Domain (requires explicit `Copyrighted=False`), CC0,
  CC BY 4.0 and CC BY-SA 4.0. Unknown/missing rights are skipped. Public Domain
  rights link to the file's Licensing section. Images are unmodified context
  thumbnails from `upload.wikimedia.org` or `thumb.wikimedia.org`, with attribution, license link, known
  title as alt text, acquisition/refresh timestamps and associated headline IDs.
  [Commons reuse obligations](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia).
  [Wikimedia thumbnail-host migration](https://phabricator.wikimedia.org/T439443)
  was verified when the controlled API response used the new hostname.
- NASA `https://images-api.nasa.gov/search`: up to three current-year **external
  video references**, official library title/ID/link and available creation date.
  Creation is not publication; channel attribution is NASA Image and Video
  Library. No video or thumbnail bytes are downloaded, no player is embedded,
  and no external audiovisual authenticity claim is made.
  [NASA library API documentation](https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf).

Every association must match the explicit term in both headline and media title.
It is labelled **Context Reference**, not a depiction or corroboration claim.
Media metadata and associations are signed in the release envelope. External
image/video bytes are **not** hashed or authenticated by that signature.

There are zero YouTube API requests. YouTube metadata is excluded to avoid
retaining expiring metadata in permanent Git history. Unsupported or missing
media shows an honest empty state; image loading failures show a source-link
fallback. CSP permits only these two explicit Wikimedia image origins; all
scripts/fonts/styles/connect requests remain same-origin, and frames are denied.

## Selection And Limits

- Target 48 hours. A missed-run window uses `min(7, max(2, ceil(gap_days)+1))`.
- Require safe canonical source URL, nonempty headline/publisher, explicit source
  policy and usable publication/discovery/source-update time. Unknown publication
  stays unknown. Acquisition records the actual successful response time.
- Deduplicate by existing canonical URL identity and SHA-256 record ID, including
  tracking-parameter normalization. A signed first-capture index retains identities even after visible pruning.
  Existing records preserve first acquisition,
  analyses and original signatures; title changes at an existing URL are not
  silently substituted into a previous captured record.
- Sort candidates by publication/discovery/source-update time and ID. Select
  round-robin across publisher names, at most eight per publisher and 48 new
  records. There is no fabricated engagement score or corroboration score.
- Retain a rolling 21 days and at most 300 visible records. Immutable signed
  releases and Git ancestry retain publication history. Empty acquisition keeps
  the prior deployed dataset unchanged, even if stale; freshness stays visible.
- The signed identity index has a hard 20,000-entry ceiling. Reaching it stops
  publication for an owner-reviewed archival decision; identities are never silently
  dropped to make old stories look new.
- Up to 110 news candidates (five sources × 16 plus GDELT × 30), max 18 HTTP
  attempts overall, six-second spacing, three attempts per endpoint, 30-second
  request timeout, 30/60-second retry delay. Retry-After is respected up to 120
  seconds; a longer delay skips that provider for the run.
- Response ceiling 2 MiB; export ceiling 8 MiB; 12 media references; up to 12
  associated headlines per media reference. Build ceiling 64 MiB, 2,500 files,
  20 MiB per asset. Workflow deadline 25 minutes. No request destination comes
  from external content, and no external content becomes a shell command.

Source categories and configured coverage areas do not overwrite model topics.
Existing offline adapters retain actual model/version/configuration receipts,
availability times, confidence, entity spans and event candidates. General and
missing evidence remain visible. Analytics use the actual published population.

## Durable State And Recovery

Branch `publication-data` contains only:

- `dataset.json`: last production-promoted export.
- `prepared.json`: null or pending release/parent digests.
- `releases/<sha256>.json`: immutable validated public exports.
- `receipts/<sha256>.json`: public production promotion receipts.

An orphan initialization avoids including repository source or private files.
The legacy v1 bootstrap is pinned to the entire committed dataset digest because
its old signatures bind records, not whole-release membership. V2 signs the whole
envelope, including membership, media, first-capture identities, sequence and parent digest.

Each write checks the exact prior branch head and uses a non-forcing Git ref
update. Concurrent siblings cannot overwrite each other. Daily and manual jobs
also share `public-showcase` concurrency with cancellation disabled. No Actions
artifact is treated as authoritative data. Bootstrap and preview staging are
explicit commands; daily execution never resets a branch or invents state.

The release is prepared **after** all gates and before deployment. Only the
atomic Pages upload changes public content. Before upload, a read-only recovery
checkpoint pins the previous successful static **production** deployment UUID,
checks its dataset against durable state and verifies its entire immutable
inventory and security headers. A resumed run can search at most 20 production
deployments for the authoritative parent; an absent target blocks upload.
Preview workflows exercise this read-only checkpoint against production too.

If upload or post-upload browser/byte checks fail, the workflow uses the
[Pages rollback API](https://developers.cloudflare.com/api/resources/pages/subresources/projects/subresources/deployments/methods/rollback/)
to restore that pinned deployment, then verifies the previous dataset, asset
hashes and headers. The run stays failed and the prepared release remains
available for explicit diagnosis/retry. Recovery uses the existing Pages Write
permission; it does not rebuild old HTML with newer code. Cloudflare API and
public-origin HTTP clients are separate so bearer credentials never reach
public assets. A hard runner timeout/cancellation can interrupt cleanup: inspect
the pinned recovery target and use the dashboard rollback before retrying if
necessary. No infrastructure can guarantee cleanup after runner termination.

Promotion requires the actual HTTPS
production manifest to match the signed release digest. If deployment fails,
current state and previous production remain. If promotion fails after a successful
upload, the next run resumes the exact prepared release, rebuilds/rechecks it,
redeploys idempotently and promotes. An independently changed production digest
or rolled-back state is rejected for explicit reconciliation. Do not force-push
the state branch or delete pending state to conceal an unsuccessful run.

## Keys, Credentials And Rotation

`daily-v1` is a distinct 32-byte Ed25519 private key; local provisioning writes
only beneath ignored `.keys/daily-publication/`. The existing local showcase key
and AES archive keys were not migrated. Only the public registry is committed.
The private key is stored as encrypted environment secret `AEGIS_PUBLIC_SIGNING_KEY`
in environment `public-daily-publication`, restricted to `main`. Signing code
also rejects Actions outside the expected repository/default-branch ref.

The registry supports active, verify-only and revoked keys. The original
`showcase` key is verify-only, so legacy record bytes remain verifiable. For a
planned rotation, explicitly provision a new key/version, retain existing public
keys, mark the old daily key verify-only (the explicit `daily-key --key-id daily-v2`
command preserves older public entries and refuses key-ID replacement), review
the registry change, configure
the corresponding environment secret, then merge and test. Signing selects the
single active reviewed daily key automatically; missing or multiple active
keys fail closed. Old keys may verify historical releases but cannot stage or
resume a new production publication after retirement. Revocation blocks both.
Historical releases may use an earlier reviewed subset of current public keys.
Revoked keys fail closed; quarantine affected records/state in a separately
reviewed recovery release rather than bypass verification.

Cloudflare uses the existing account-owned token “Aegis News Pages Publication,”
Pages Write for account `3de5bfe983584a2eab1cbb710aa4fbe8`, stored as repository
secret `CLOUDFLARE_API_TOKEN`. It covers all Pages projects in that account, not
one project. `apps/showcase/deployment.json` pins token ID, account/project,
reviewed permissions and the verified expiry **13 January 2027 23:59:59 UTC /
14 January 2027 05:29:59 IST**. Every deployment
verifies live token identity/status/expiration and checks the Direct Upload project has no
runtime bindings or environment variables. The minimally scoped token cannot
read token policies; the exact permission scope is owner-reviewed attestation,
not an automatic live policy proof. Any scope/expiry/identity change requires a
fresh reviewed attestation. Do not broaden the credential just to inspect itself.

No signing/deployment credentials are attached to PR-triggered jobs. Checkout
does not persist Git credentials. The daily job's GITHUB_TOKEN has contents-write
for the public data branch; signing and Cloudflare secrets exist only in their
necessary steps. It has no PR/issue/admin permissions. The manual publisher is
still available; production manual deployment is blocked while daily publication
is active to prevent state divergence. Use the daily workflow's manual dispatch
to refresh active production.

Credential-bearing publication workflows pin checkout, setup-uv, pnpm setup and
Node setup to verified upstream commit SHAs. Tool package versions and lockfiles
remain fixed. Review dependency/action updates through normal source changes.
Both publishers also run the Python and production Node dependency audits on
each execution; a newly reported advisory blocks deployment until reviewed and
patched, even if the last source-code CI run was green.

## Commands

From a trusted local checkout, with the dedicated ignored local key:

```powershell
uv run python -m scripts.public_showcase state-read
uv run python -m scripts.public_showcase daily --previous .data/daily/previous.json --key-file .keys/daily-publication/daily-v1.key
uv run python -m scripts.public_showcase validate --dataset .data/daily/candidate.json
uv run python -m scripts.public_showcase build --dataset .data/daily/candidate.json
uv run python -m scripts.public_showcase audit --dataset .data/daily/candidate.json
node apps/showcase/check-browser.mjs
```

No output candidate means no changed release; do not deploy a stale candidate
from an earlier local run. Use a fresh output path for each manual experiment.
The workflow uses fresh ephemeral checkouts and resumes prepared state explicitly.

To validate/deploy a preview without production promotion, use `state-stage
--dataset <candidate> --expected-head <state-head> --preview`, then dispatch the
registered `ci.yaml` entry point with `public_showcase=true`, exact `export_sha256`
and `release_sha256`, `preview=true`, `deploy=true`, on the reviewed feature ref.
This uses the existing encrypted deployment token but never the environment
signing key. Preview staging retains the immutable release without changing the
active dataset or pending production release.

After approved integration/activation:

```powershell
gh workflow run daily-publication.yaml --ref main
gh run list --workflow daily-publication.yaml --limit 5
```

Inspect the run summary, production `/data/manifest.json`, browser verification
and matching `publication-data` receipt. A green acquisition log alone is not a
successful publication. Disable unattended runs by setting the activation
variable to `false`; this preserves the public static site.

## Cost

Cloudflare and provider incremental cost is **USD $0/month**: existing Cloudflare Pages Free,
static `pages.dev`, no Functions/Workers/bindings, R2, D1, KV, paid API, database,
container or hosted private service. **GitHub reports this repository is private.**
Private-repository hosted Actions consume an account's included allowance and can
incur charges beyond it. The earlier public-repository assumption was incorrect.
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Daily execution is ~30–31 runs/month, capped at 25 minutes each (at most 775 runner
minutes for daily runs alone), plus existing CI and explicit previews. Available
allowance, account-wide use and paid-usage blocking could not be verified: the
current API credential lacks billing scope and browser policy blocks billing UI.
No broader credential scope, repository visibility change, payment or plan
upgrade was requested or performed. **Total $0 cost is conditional, not confirmed.**

Before publication or unattended activation, the owner must confirm an
applicable Actions hard $0 spending budget has **Stop usage when budget limit is
reached** enabled (or equivalent account-enforced paid-usage blocking), and that
the included runner allowance covers expected use. Only then set repository
variable `ACTIONS_PAID_USAGE_DISABLED=true`. This variable is an owner attestation,
not live billing proof. An unknown/false value prevents both publication jobs
from allocating a runner. If included minutes are exhausted, retain the last
valid website until the allowance resets; do not enable paid usage. Regular
repository CI is unchanged and must be considered in the account budget too.
See [GitHub's budget instructions](https://docs.github.com/en/billing/how-tos/set-up-budgets)
for the spending-block setting; notification-only budgets do not stop charges.

### Controlled Final CI

The owner separately authorized one complete hosted validation attempt and, only
for an established issue, one targeted retry while this repository stays private.
This limited authorization does not attest a hard $0 budget. Keep both
`ACTIONS_PAID_USAGE_DISABLED` and `DAILY_PUBLICATION_ENABLED` unset unless their
separate documented prerequisites are met.

The existing CI workflow's `validation_only` input runs backend, frontend,
migrations and security checks. Backend tests include publication/signing/state
and recovery cases. It skips both the full private demo-stack job and the
publication job, even if publication inputs are also supplied. It receives no
signing/deployment secrets in any executing job and does not deploy or acquire
news. The publication billing guards remain unchanged.

```powershell
gh workflow run ci.yaml --ref feat/daily-publication -f validation_only=true -f public_showcase=false -f deploy=false
```

Use a CI skip marker on the preparation/ledger commits to avoid duplicate
push/pull-request runs, then dispatch exactly once. Count reruns against the
owner's two-attempt ceiling; retry only the failed job(s) after diagnosis. Do not
start a second complete workflow or use the private-demo dispatch for this task.
Read-only billing APIs can remain unavailable; repository run-timing data and
observed job durations do not prove account quota, charges or a hard spending block.

For an established frontend-only failure, `frontend_only=true` together with
`validation_only=true` runs the complete frontend job without repeating the three
successful jobs. It cannot select publication or the private demo. This consumes
the one permitted targeted retry, not a new complete attempt:

```powershell
gh workflow run ci.yaml --ref feat/daily-publication -f validation_only=true -f frontend_only=true -f public_showcase=false -f deploy=false
```

CI browser tests use the already built Next standalone production server with
its static assets and two workers. Local interactive tests retain the development
server. All test assertions, existing skips, retries and timeouts are unchanged.

Cloudflare Free permits 500 builds/month, 20,000 files/site and 25 MiB/asset;
this implementation enforces lower asset limits and builds on GitHub. Static
asset requests are free/unlimited; Functions are not used. Account-wide limits
can be shared with other projects. Review [Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
and [pricing](https://pages.cloudflare.com/) before expanding usage.
Release Git history grows over time (public metadata only); monitor repository
size and review a future archival policy before it becomes operationally large.

## Validation And Remaining Integration

See `daily-publishing-ledger.md` for measured source counts, exact preview release,
workflow/CI run links and results. Activation is a distinct owner-approved step;
no autonomous feature-branch merge is performed.

Latest verified preview: [73-record edition](https://daily-preview.aegis-news-showcase.pages.dev/),
[successful publication run](https://github.com/itsmanudon/aegis-news/actions/runs/39647028765),
updated **21 October 2026 17:42:50 UTC / 23:12:50 IST**. It contains 37 NASA,
26 GDELT, eight USGS, one Federal Reserve and one NIST reference, across 29
publisher names, with three Commons images and three NASA video references.
GDELT acquisition uses English-language discovery. This is a bounded recent-news
collection with a 21-day archive, not a comprehensive ranking of world news.
No external reporting is independently corroborated by cryptographic validity.

Current integration status and remaining publication steps:

1. PR #3 is merged at `319c503`; [main CI](https://github.com/itsmanudon/aegis-news/actions/runs/39790652247)
   passed backend, migrations, security and frontend. PR #2 history is intact.
2. For the owner-authorized local trial, follow **Manual Publication From macOS**:
   match the existing signing key, supply the reviewed local Cloudflare token,
   run the dry run, then explicitly invoke `--publish` only if every gate passes.
3. Verify the live signed release and durable receipt. Keep both hosted control
   variables unset. A local success does not authorize a hosted run or schedule.
4. Any later hosted publication/activation requires its own authorization and
   hard paid-usage blocking prerequisite below. No such activation occurs here.

### Hosted First Production Trial Acceptance

This separate hosted procedure requires owner approval and the hosted cost guard.
It is not the local publication path. None of its dispatch/activation commands
was executed during final CI validation or local-publisher implementation.

1. Review the final PR and its recorded tested revision/results, then approve a
   normal merge of PR #3 into `main`, preserving feature history. Confirm the
   resulting default-branch commit and workflow registration. Wait for required
   main CI under separately authorized usage before dispatching publication.
   Do not rebase or move release tags.
2. Independently verify the documented hard paid-usage blocking prerequisite and
   record `ACTIONS_PAID_USAGE_DISABLED=true` only after it is established. The
   owner's allowance for limited CI runs is not proof of this requirement.
   Leave `DAILY_PUBLICATION_ENABLED` absent. Neither secret needs rotation for
   the trial; a missing/mismatched secret must stop publication.
3. Read and verify `publication-data` against production before dispatch. At the
   current handoff, the branch head is `39e75100…3c0b`, current release digest is
   `be21a984…96129f`, 40 records, and `prepared.json` is null. Re-read these values
   at execution time; stop to reconcile any unexpected change.
4. With explicit production-trial approval, dispatch exactly once:

   ```powershell
   gh workflow run daily-publication.yaml --ref main
   ```

5. Confirm all actual gates pass: trusted-main environment access; dedicated
   signing secret matches reviewed active `daily-v1`; live Cloudflare credential
   identity/status/expiry and static destination; bounded licensed acquisition;
   canonical SHA-256/Ed25519 evidence; unit/security/dependency checks; static
   inventory and desktop/mobile browser acceptance; CAS preparation; verified
   previous-production recovery checkpoint; atomic upload; live byte/header and
   browser verification; CAS durable promotion.
6. Compare the new signed release digest across production
   `/data/manifest.json`, the cryptographically validated
   `/data/dataset.json`, `publication-data/dataset.json` and
   `receipts/<digest>.json`. Confirm source commit is the approved main revision,
   sequence advances by one, parent is the previous validated release, first
   acquisitions/legacy signatures remain intact, and `prepared.json` returns to
   null. Use the actual new counts, not the old 73-record preview count.
7. An empty acquisition is a legitimate no-op, not proof of a complete first
   deployment/promotion trial. A failed run must stay failed: inspect recovery,
   preserve prepared state/history and verify the old live release. Do not bypass
   guards, erase pending state, force-update Git refs or activate the schedule.
   A hard timeout can require explicit owner-led Cloudflare recovery.
8. Only after a complete successful trial, present its run URL, signing/crypto
   results, production URL/digest/timestamp, recovery checkpoint and durable
   receipt. Request separate owner approval to set
   `DAILY_PUBLICATION_ENABLED=true`; do not infer activation approval from the
   merge or trial approval.

The configured signing secret exists, but its actual encrypted value cannot be
read back for inspection; the main-only trial must prove it matches reviewed
`daily-v1`. The Pages token has been verified through the real preview workflow;
rotate it before **14 January 2027 05:29:59 IST**. No missing secret names are
known. The owner's limited validation authorization completed hosted backend,
security, migrations and frontend gates: see the exact revisions and two runs in the
execution ledger. The frontend retry passed 103 browser tests with 11 existing
skips; the first attempt's three timeouts were corrected through production-mode
test serving and two workers, without changing assertions or timeouts.

PR #3 has since been merged and main CI passed. The hard paid-usage block remains
unverified, so `ACTIONS_PAID_USAGE_DISABLED` stays unset. First hosted environment
signing/promotion and schedule activation still require separate approval and the
acceptance above. The subsequent local path uses an already matching local key
and this computer, with both hosted controls unset; it never retrieves encrypted
Actions secrets or dispatches a workflow.

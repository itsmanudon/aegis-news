# Live multimedia validation — 4 October 2026 UTC

The local run continued into 5 October in Asia/Calcutta.

This records a bounded local development acceptance run, not a production feed,
rights clearance, or model-quality benchmark. Gold v3 is unchanged. Raw upstream
responses, article dumps, credentials and runtime data are not committed.

## Baseline and implementation

Historical loader was fast-forwarded from main `71132477b4471a37c2976217bb90be4a1843e4f3`
to `b0e86b9156258800ab75ca9de0929f9e587d037c`, pushed, and its
[hosted CI completed successfully](https://github.com/itsmanudon/aegis-news/actions/runs/37219753932).
Existing release tags were preserved. Work then moved to `feat/live-multimedia-providers`.

The default document view previously drained the corpus and fetched intelligence
per document before rendering. It now reads 20 summaries, supports cursor navigation,
and loads intelligence only on detail. The volume browser test asserts zero
intelligence requests during feed navigation, fewer than 30 API responses, and no
429 responses. Rate limits were not increased.

Provider articles use normal authenticated Source creation and ingestion POSTs,
then the existing Temporal normalization/Offline AI/provenance pipeline. New tables
only stage acquisition identities, first submission inputs, provider evidence,
run reports, and mutable YouTube references. `live_providers_0001` follows
`mvp_merge_0001`; no old revision was rebased.

## Live outcomes

All four keys were present in API; GDELT requires none. Presence is not account
acceptance. Counts below exclude the deliberate repeated GNews poll.

| Provider | Article observations fetched | New canonical ingestions | Duplicate observations | Image references observed | Video references stored |
| --- | ---: | ---: | ---: | ---: | ---: |
| NewsData | 32 | 32 | 0 | 32 | 0 |
| NewsAPI | 22 | 21 | 1 | 19 | 0 |
| GNews | 22 | 16 | 6 | 22 | 0 |
| GDELT | 0 | 0 | 0 | 0 | 0 |
| YouTube | 0 | 0 | 0 | 0 | 10 |

76 article observations produced **69 new completed documents**, with seven duplicate
observations. There are 73 distinct provider evidence records and 66 distinct
image-bearing canonical articles. Images are remote references; that count does
not certify every publisher URL remains available. Browser acceptance confirmed
at least one image decoded, with fallback rendering available for failures.

The exact successful GNews India poll was repeated: 20 fetched, **zero submitted**,
20 duplicates, 17 distinct previously completed workflows. Including this repeat,
GNews observations total 42 and duplicate observations total 26; across all runs,
article observations total 96 and duplicates total 27. No duplicate canonical
records were created by the repeated poll.

YouTube refresh returned ten references and removed zero unavailable IDs. Expiry,
metadata replacement and deletion of missing IDs were also tested using synthetic
fixtures. YouTube metadata never enters analyses, raw objects or signed provenance.

| Local record type | Before | After |
| --- | ---: | ---: |
| Documents | 3,024 | 3,093 |
| Historical corpus documents | 3,000 | 3,000 |
| Sources | 6 | 44 |
| Analyses | 13,176 | 13,496 |
| Canonical entities | 4 | 4 |
| Events | 145 | 148 |
| Stored document-media links | 8 | 8 |
| Provider article/document links | 0 | 69 |
| YouTube references | 0 | 10 |

The unchanged stored-media count is deliberate: publisher images are not fabricated
MinIO objects. Unresolved entity output is not promoted into invented canonical
entities. All sampled article analyses used `local-baseline` (Offline).

### Failures and corrections

- Initial GNews HTTP 403 required account/email activation. The user completed it;
  a two-item smoke run then completed successfully. No authentication bypass was used.
- A GNews multi-page run returned HTTP 429. No automatic 429 retry was made. Shared
  outbound pacing was increased from 1.1 to 2.1 seconds; one subsequent bounded
  run and its idempotency repeat succeeded. Failed-request counts now include
  attempted upstream requests. Older failed reports had zero in this counter and
  must not be interpreted as zero quota usage.
- GDELT remained unavailable with connection timeout, both in the API container
  and a separate local diagnostic. Three bounded transport attempts were made in
  the initial run, plus one diagnostic. No HTTPS/allowlist protection was weakened.
  Its live acceptance is **not passed**; the other providers continued successfully.
- Initial regression checks caught stale endpoint/migration-head/demo-env assertions;
  they were updated for the new contracts. The mock browser request allowlist was
  updated for the two new presentation routes. A final review also caught an empty
  outcome for a single disabled provider; a regression test reproduced it before
  the fix. All final relevant checks passed.

Quota exposure was small: four successful NewsData requests, three NewsAPI requests,
five successful GNews requests (including repeat), two YouTube searches and three
YouTube details requests (including refresh). GNews activation and 429 attempts are
additional; exact account quota usage requires its dashboard. No large live fetch
or continuous polling was performed.

## Verification evidence

- Samples from **each of the three successful article providers** returned five
  analyses and eleven provenance records; hash/content/chain/signature checks were
  all true. Search found each sampled document; similarity returned three results.
- Real API browser tests passed for unfiltered Dashboard, paginated Documents,
  Entities, Events, multimedia, decoded remote image, document intelligence,
  provenance verification and enabled admin controls. Mock browser flows also passed.
- Real viewer fetch returned 403; anonymous fetch returned 401. Permission-denied
  requests made no upstream calls. Provider operations produced ten fetch/refresh
  audit records at the recorded count checkpoint; subsequent verification adds
  integrity/signature and permission-denied audit records.
- Source publishers are independent of provider labels. UI never replaces real
  acquisition failures with mock success. Captured excerpts are not full articles.
- Repository and captured API/worker logs had zero matches against configured
  provider key values; no JWT pattern appeared in those logs. Only match counts
  were reported. No raw sensitive payload was printed.

## Local validation

`make` was unavailable on this Windows machine. The commands in `make check` were
executed individually, with a process-only CORS setting for the test environment:

```powershell
$env:AEGIS_CORS_ORIGINS='["http://localhost:3000"]'
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -q
uv run python scripts/scan_secrets.py
uv run python scripts/export_schemas.py --check
pnpm.cmd web:api:check
pnpm.cmd web:test
pnpm.cmd web:lint
pnpm.cmd web:typecheck
pnpm.cmd web:build
```

Final backend suite: **298 passed, 36 optional integration/E2E tests skipped**.
Provider-focused tests: 59, included above. Strict mypy: 114 source files, no errors.
Frontend: **16 unit/component tests**, **10 mock Playwright flows**, and **two real
provider/volume browser flows** passed. Formatting, lint, generated types/OpenAPI
drift, production build, repository secret guard, and Python/frontend dependency
audits passed. Existing Starlette/httpx test-client deprecation warning remains.

Disposable database migration verification exercised upgrade/head, metadata check,
downgrade to foundation, re-upgrade, downgrade/base, and re-upgrade/check. It passed.
Existing demo DB was only upgraded, never downgraded/reset; current head is
`live_providers_0001`. No existing volume was destroyed.

Normal CI is unchanged: CPU-safe Offline, no upstream calls, credentials or model
downloads. Provider browser acceptance is explicitly local/opt-in. Hosted feature
CI status and exact final SHA are recorded in the handoff, rather than claiming
that local checks certify the hosted environment.

## Reproduce / inspect

See [provider contracts, restrictions and commands](live-providers.md). Start the
supported full stack with `python scripts/demo.py start`; do not reset existing data.
Keys are read only by API. Optional Doppler project injection is documented, but
the actual acceptance used local `.env`; Doppler account execution was not tested.

```sh
uv run python -m aegis.providers fetch-all --limit-per-provider 2 --query technology
uv run python -m aegis.providers fetch --provider newsdata --limit 20 --query "technology OR business OR economics"
uv run python -m aegis.providers fetch --provider newsapi --limit 20 --query "markets OR companies OR cybersecurity OR public policy"
uv run python -m aegis.providers fetch --provider gnews --limit 20 --query "business OR economics OR technology OR policy OR commodities OR cybersecurity" --country in
uv run python -m aegis.providers fetch --provider newsdata --limit 10 --query "cybersecurity OR AI OR companies" --country us
uv run python -m aegis.providers fetch --provider youtube --limit 8 --query technology
uv run python -m aegis.providers refresh-youtube
```

Results can change with provider freshness, quota and ranking. Use small calls first;
do not keep retrying an unavailable/quota-limited provider. Reruns reuse persisted
acquisition aliases/frozen ingestion requests; `--retry-failed` uses the existing
Temporal failed-only retry policy. Acquisition interruption itself is reported as
interrupted, and requires a manual rerun; article processing is durable Temporal.

Running local services: frontend `http://localhost:33000`, API docs
`http://localhost:38000/docs`, Temporal `http://localhost:38233`, Grafana
`http://localhost:33001`, Prometheus `http://localhost:39090`, MinIO console
`http://localhost:39001`, Loki `http://localhost:33100`. Stack remains running.

## Limits / next review

Manual acquisition currently assumes one API process, with no scheduler or
production-wide quota coordination. Headline equality can merge generic stories;
ambiguous alias conflicts are skipped rather than silently reassigned. Remote
media is neither copied nor cryptographically verified. YouTube reference TTL is
29 days, with hourly/list-time deletion and manual refresh; backups/export retention
must also respect policy. This is not an audited production-compliance claim.

Three article providers passed real acceptance, with GDELT still network-blocked.
Provider/source copyright and free/developer-plan restrictions still apply. No live
data or model-quality claims are attached to Gold v3. The local database is now on
the feature migration; review/merge the branch before running its migration history
from main. No automatic feature merge or release-tag change was performed.

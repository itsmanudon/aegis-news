# Manual live/delayed multimedia acquisition

Local academic development only. Gold v3 remains the reviewed evaluation reference;
provider snippets are neither gold annotations nor verified facts. Offline inference
is the default worker profile. No publisher scraping, video downloads, image proxy,
continuous polling, model tuning or production deployment is introduced.

## Official contracts checked 4 October 2026

Account dashboards and subscription terms control actual entitlements. “Enabled” in
the API means a key is present, not that the account or quota has been accepted.

| Provider | Key / variable | Official endpoint | Free/development allowance and freshness | Text / images / video | Storage and attribution |
| --- | --- | --- | --- | --- | --- |
| NewsData.io | `AEGIS_NEWSDATA_API_KEY` | `https://newsdata.io/api/1/latest` | 200 credits/day, 10 items/page, 30 credits/15 minutes; 12-hour delay, latest 48 hours | headline/description; image and video URLs; free content not full text | Third-party rights retained; show publisher/provider/original URL; no image mirroring |
| GNews | `AEGIS_GNEWS_API_KEY` | `https://gnews.io/api/v4/search` | 100 requests/day, 10 items/request, 1 request/sec; 12-hour delay, 30-day history | headline/description, truncated content and image URL; no video field | Development/testing plan; reasonable caching permitted, substantial competing archives forbidden; provider credit shown |
| NewsAPI.org | `AEGIS_NEWSAPI_API_KEY` | `https://newsapi.org/v2/everything` | Developer 100 requests/day; 24-hour delay, one-month history | headline/description, 200-character content, `urlToImage`; no video | Developer plan limited to development, not staging/production; retain notices and source/author attribution |
| GDELT | none | `https://api.gdeltproject.org/api/v2/doc/doc` | No documented contractual quota/SLA; conservative manual calls, recent window | headline/link/domain/social-image, not article body; no video | Cite/link GDELT; linked publisher content/media rights separate |
| YouTube | `AEGIS_YOUTUBE_API_KEY` | `https://www.googleapis.com/youtube/v3/search`, `/videos` | Current docs: separate 100 search calls/day (1 each), other endpoints 10,000 units/day; midnight Pacific reset | refreshable title/channel/date/thumbnail and official watch link | Limited non-authorized metadata: refresh/delete within 30 days; no audiovisual downloads, no automatic derived intelligence |

NewsData uses `X-ACCESS-KEY`, `results` and opaque `nextPage` → `page`.
Publisher fields are `source_name/source_url`; missing author/date stay null.
Both HTTP and error-envelope failures are checked. Official
[OpenAPI](https://newsdata.io/openapi.json), [documentation](https://newsdata.io/documentation),
[plans](https://newsdata.io/blog/pricing-plan-in-newsdata-io/),
[limits](https://newsdata.io/blog/newsdata-rate-limit/) and
[terms](https://newsdata.io/terms) preserve third-party ownership and do not grant
blanket republication or image-cache rights. Terms were read in the rendered page.

GNews uses query `apikey`, numeric `page`, `max` and `totalArticles/articles`;
pagination stops at 1,000 upstream items. Current records include `id`, `lang`,
`source.name/url`, `image`, `publishedAt`. Our manual run is capped much lower.
403 may indicate daily exhaustion; 429 indicates throttling. No aggressive retry.
See [authentication](https://docs.gnews.io/authentication),
[search](https://docs.gnews.io/endpoints/search-endpoint),
[response](https://docs.gnews.io/json-response), [errors](https://docs.gnews.io/error-handling),
[plans](https://gnews.io/) and [terms](https://gnews.io/legal/terms-of-service).
The small local demo is not permission to systematically archive substantial API
content or redistribute publisher articles. Termination requires ceasing use and
destroying downloaded material. Public/commercial use needs separate rights review.

NewsAPI uses `X-Api-Key`, `page/pageSize`, `status/totalResults/articles`.
`/everything` has no country parameter; the selected geography is included in the
query. `source.id/name` is publisher attribution, not provider identity. This adapter
uses descriptions, never presents truncated `content` as a complete article.
See [endpoint](https://newsapi.org/docs/endpoints/everything),
[errors](https://newsapi.org/docs/errors), [plans](https://newsapi.org/pricing) and
[terms](https://newsapi.org/terms). HTTP 401/403/429 and structured provider errors
stop that provider without failing other providers.

GDELT uses `mode=artlist&format=json`, a bounded `maxrecords`, and a recent
`timespan`. DOC has no documented page cursor; one result window is fetched.
Discovery `seendate` remains acquisition metadata, never a publisher timestamp.
The [DOC 2.0 guide](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) describes
250 maximum results and image discovery. Our limit is 30. Dataset reuse with
attribution is described on [GDELT About](https://gdeltproject.org/about.html);
it does not transfer linked publisher copyright. No guaranteed full text or SLA.

YouTube search uses `part=snippet&type=video`, `nextPageToken/pageToken`; a
`videos.list` check refreshes returned IDs. See [search](https://developers.google.com/youtube/v3/docs/search/list),
[videos](https://developers.google.com/youtube/v3/docs/videos/list),
[current quotas](https://developers.google.com/youtube/v3/determine_quota_cost) and
[developer policies](https://developers.google.com/youtube/terms/developer-policies).
The current separate search bucket differs from older 100-general-unit guidance.
No analytics-policy amendment is assumed. Metadata is excluded from NewsDocument,
AnalysisResult, object storage and immutable signed provenance.

## Configuration and Doppler

Four individually optional backend `SecretStr` keys are listed, empty, in
`.env.example`. Missing one disables only that provider. GDELT needs none.
Never put keys in `NEXT_PUBLIC_*`, browser requests, command arguments or Git.

The existing demo launcher reads local `.env` first, then portable demo port/profile
settings. Provider keys go only into the API container, not web or workers.

```sh
python scripts/demo.py start
# Equivalent, preserving existing volumes:
docker compose --env-file .env --env-file infrastructure/demo.env.example -p aegis-demo --profile full up -d --build

# Optional; project aegis-news. Doppler is not a dependency or a CI prerequisite.
doppler setup --project aegis-news
doppler run -- python scripts/demo.py start
doppler run -- python -m aegis.providers fetch-all --limit-per-provider 3
```

Restart/recreate API after changing its injected secrets. Running the CLI under
Doppler alone does not replace secrets already inside an existing API container.
Do not print `docker compose config`/container environment or enable HTTP debug logs
when keys are injected. HTTPX INFO is suppressed because query-auth URLs can leak keys.

## Quota-safe manual commands

```sh
uv run python -m aegis.providers fetch --provider newsdata --limit 2 --query technology
uv run python -m aegis.providers fetch --provider gnews --limit 2 --query technology
uv run python -m aegis.providers fetch --provider newsapi --limit 2 --query technology
uv run python -m aegis.providers fetch --provider gdelt --limit 5 --query technology
uv run python -m aegis.providers fetch --provider youtube --limit 2 --query "technology news"
uv run python -m aegis.providers fetch-all --limit-per-provider 10 --query "technology OR business OR economics"
uv run python -m aegis.providers demo --limit-per-provider 10 --query "India OR policy OR commodities OR cybersecurity" --country in
uv run python -m aegis.providers status --run-id <returned-run-id>
uv run python -m aegis.providers refresh-youtube
```

CLI uses the existing local development admin issuer, with tokens captured in memory,
or `--token-env AEGIS_ACCESS_TOKEN` for an existing delegated identity. It calls only
the real protected local API. Tokens are refreshed for local polling, not persisted.
One run at a time; limit 1–30/provider (YouTube capped at 10). Each news adapter uses
at most three pages. YouTube search uses at most two plus one details request.
Countries `in/us` are optional; omit for global acquisition. Queries are human inputs,
never expected model labels. Mix general topics across several small runs.

## Persistence, retries and multimedia boundaries

Article acquisition staging fixes the first submitted Article JSON and stable
idempotency key. Aliases use provider ID, canonical URL (tracking/fragment removed),
then exact normalized headline. Headlines shorter than 10 normalized characters
do not merge across providers; generic longer headlines can still collide.
This is conservative equality, not event clustering; ambiguous alias conflicts are
skipped. Evidence from each provider is retained separately, with original links.
Sources represent publishers (or the actual publisher domain), not API providers.

Articles always POST through normal source/ingestion authorization, validation,
audit and Temporal. Reruns reuse workflow IDs; changed snippets cannot change the
frozen ingestion fingerprint. An interrupted pre-submission stage can resume.
Use `--retry-failed` to resubmit frozen inputs; Temporal's existing failed-only policy
reuses running/completed workflows. This does not reanalyze existing documents.

Runs persist safe counts/IDs, not response blobs or credentials. On API process
interruption they are marked interrupted on the next provider operation; rerun the
query to recover staged inputs. Acquisition itself is a bounded manual API task,
not a newly scheduled Temporal crawler. Article processing remains durable Temporal.
This local baseline assumes one API process; horizontal acquisition orchestration
and publisher source creation under multiple processes are not production-qualified.

HTTPS remote image references are separate acquisition evidence, not fictitious
MinIO objects/MediaAssets. Browser images use no-referrer, lazy loading, safe URL
validation and a broken-image fallback. Backend never fetches them. Integrity
verification covers captured article bytes and immutable intelligence, not remote
images, which can change independently.

YouTube metadata is mutable and expires after 29 days. Hourly local housekeeping
and list-time pruning delete expired references; manual refresh updates metadata
and deletes requested IDs missing from `videos.list`. Protected DELETE is also
available. UI links to official YouTube, with thumbnail/channel/time, no autoplay
or downloads. All intelligence displayed elsewhere is AegisNews output, not YouTube.
Backups/export retention must also respect deletion; this local implementation is
not a claim of audited production YouTube compliance. No YouTube description/statistic
archive or derived model output is stored.

## Protected API and tests

- `GET /api/v1/providers`
- `POST /api/v1/providers/{provider}/fetch`, `POST /api/v1/providers/fetch-all`
- `GET /api/v1/provider-runs/{run_id}`
- `GET /api/v1/provider-articles`, `GET /api/v1/documents/{id}/acquisition`
- `GET /api/v1/youtube-references`, `POST /api/v1/youtube-references/refresh`
- `DELETE /api/v1/youtube-references/{video_id}`

Fetch/config/status/refresh/delete require `sources:write` and `ingestions:write`;
read presentation endpoints require `documents:read`. Role capabilities still constrain
delegated token scopes. Secrets never appear in responses. Provider operations create
allowlisted audit events. Fixed provider names label counters, never URLs/headlines.
`items_ingested` counts accepted ingestion submissions, not Temporal completions;
use run workflow statuses to confirm actual completion. Counters reset on API restart.
Fixtures are original synthetic examples; normal CI never fetches external APIs.
Schema and generated TypeScript drift checks remain mandatory.

Measured local outcomes, failures and validation are recorded in the
[acceptance ledger](live-provider-validation.md). GDELT was network-unavailable
during that run; key presence must never be shown as successful live acceptance.

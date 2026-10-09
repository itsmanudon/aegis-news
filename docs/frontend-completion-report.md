# Aegis News — Completion Sprint Report

## Executive Summary

The remaining redesign is implemented on `feat/aegis-editorial-foundation`.
Media Lab, exact-model Topic Intelligence, bounded chronological discovery and
SQL-backed Intelligence Analytics share the existing editorial application,
providers, identity boundary and security semantics. Existing routes remain.
Real isolated ingestion, search, stored evidence, verification, topic membership,
analytics and scope-denied journeys were exercised; the release candidate does
not depend on mock-only demonstrations.

Source reporting, model outputs and cryptographic evidence remain distinct.
Signed lineage establishes captured-byte integrity, not factual accuracy,
production C2PA compliance or an externally trusted timestamp. No ML algorithm,
cryptographic primitive, ingestion worker, canonical schema or production data was
changed. No merge, push, deployment, release-tag change or history rewrite occurred.

## Git and Checkpoints

- Branch: `feat/aegis-editorial-foundation`.
- Verified clean starting commit: `c1600b07a6ce523e08cd4b3ce1234ac8a1f1c6b5`.
- Observed local/remote-main baseline: `49a55e583b93d506d654fe5baf102fed15cc9dc0`.
- `5783a010e97730066ca1277c71a0e38d68223470`: Media Lab and shared read-contract
  foundation. The backend, generated adapters and chart primitives landed together
  to keep the boundary buildable; Topic/Analytics pages were explicitly pending.
- `8bebe125b0629b8bbb43a1eff4a26775ebc8ad99`: Topic dossiers, Intelligence
  Analytics, chronological discovery, navigation and focused regression tests.
- `eff60ea2d386da309ca72be7e6f84abd9e895886`: isolated actual product journeys, guarded runtime and security validation.
- `5cb690c37e43436fc0ea1c8d8fb8449262bc55b4`: final validated implementation,
  accessible product regression gates, editorial loading stability and font
  performance. All product changes are included through this commit.

This report's documentation commit follows the validated implementation commit.
The owner's final handoff records the resulting branch-tip SHA; `git rev-parse HEAD`
resolves that documentation tip without a self-referential commit hash in this file.
The execution history and verification rulings are in
[the completion ledger](frontend-completion-ledger.md).

## Navigation and Route Map

One Next.js application and shared identity/query boundary remain. A single active
navigation indicator identifies the current experience. Mobile navigation supports
keyboard activation, Escape and focus restoration. Mode, authentication and the
in-memory token controls remain visible. Authenticated tokens are cleared from the
input after submission and remain absent from deliberate captures.

| Experience            | Route                          | Function                                                                                 |
| --------------------- | ------------------------------ | ---------------------------------------------------------------------------------------- |
| News & Intelligence   | `/`                            | Editorial Discover; globally publication-ordered bounded reporting, unknown times last   |
| News & Intelligence   | `/discovery`                   | Cursor chronology; publication or first seen; source/query/topic/window/cutoff filters   |
| News & Intelligence   | `/documents`                   | Existing paginated archive, filters, responsive rows/table and evidence disclosures      |
| News & Intelligence   | `/documents/[id]`              | Existing full Story Detail, source text, available assessments and explicit verification |
| News & Intelligence   | `/search`                      | Existing literal reporting search and expandable source evidence                         |
| News & Intelligence   | `/entities`, `/entities/[id]`  | Existing canonical directory and paginated linked evidence                               |
| News & Intelligence   | `/events`                      | Existing revision-safe source/model event browsing and timestamps                        |
| News & Intelligence   | `/topics`, `/topics/[id]`      | New recorded-cohort directory and research dossier                                       |
| News & Intelligence   | `/analytics`                   | New explicit-population coverage, source and sentiment analysis                          |
| News & Intelligence   | `/multimedia`                  | Media Lab: remote references and selected stored attachment records                      |
| News & Intelligence   | `/provenance`                  | Existing focused verification workspace; explicit authorized mutations                   |
| Operations & Security | `/operations`                  | Existing operational overview and bounded exception/timeline views                       |
| Operations & Security | `/sources`                     | Existing source administration, ingestion, known workflows and provider controls         |
| Operations & Security | `/sources#provider-operations` | Existing provider administration anchor, preserved                                       |
| Operations & Security | `/security`                    | Existing scope context and server-reported audit history                                 |

The masthead adds Topics and Analytics. Chronological Discovery is linked from
Discover and analytics drilldowns. Operations and existing functional URLs were
retained rather than migrated.

## Frontend Architecture and Design Decisions

```text
RootLayout: pinned local fonts
└─ Providers: mode + in-memory token + isolated query client
   └─ Shell / Masthead: editorial and operational navigation
      ├─ Discover → StoryLead / StoryRow / StoryMetadata / DiscoveryMedia
      ├─ Topics → TopicIdentity / CursorPager
      ├─ TopicDetail → TopicEvidence / EvidenceDisclosure / Timestamp
      ├─ Analytics → Population / CoverageChart / Distribution / Exact Tables
      ├─ ChronologicalDiscovery → EditorialResults / EvidenceDisclosure
      ├─ MediaLab → RemoteImage / Article References / Video References
      │             / Selected Stored Attachment Inspector
      └─ Existing Story, Entity, Event, Verification and Operations pages
```

Paper, Ink, Teal, warm-neutral filters, white data surfaces and subdued separators
are retained. Editorial rows carry the hierarchy; technical information stays in
rounded 12px disclosures. Source Serif 4 carries editorial headings and excerpts,
Inter controls and quantities, and monospace exact machine identifiers. Authored
labels use Title Case; source headlines and model labels retain their supplied
case. Charts use small SVGs, native meters and accessible exact tables without a
chart framework. There is no decorative motion or new UI framework.

Expanded panels reuse native disclosures with labelled regions, separate full-story
links, visible focus and Escape restoration. Loaded topic assessments expand
without extra requests. Full Story links open the current complete record; query
cutoffs do not imply historical reconstruction of article prose or mutable metadata.

Measured polish corrected narrow date input sizing, inherited table-header nowrap,
scaled SVG labels and a missing chronological section heading. Chart date/scale
labels now use normal HTML at 12px rather than shrinking with SVG geometry.
The archive loading state reserves reading space. Source Serif's fallback metrics
use the installed Next.js-supported Times New Roman adjustment. The desktop-only
italic masthead face is not preloaded; its original local bytes and license remain.

## Backend and Generated Contracts

Exactly five additive protected read endpoints were introduced. All use existing
response envelopes, request IDs and `documents:read` authorization.

| Endpoint                                  | Supported Contract                                                                            |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| `GET /api/v1/topics`                      | Label search, bounded cohorts, frozen cutoff and deterministic cursor                         |
| `GET /api/v1/topics/{topic_id}`           | Exact identity, unique-document count and selected availability                               |
| `GET /api/v1/topics/{topic_id}/documents` | Source-attributed membership, selected analysis/confidence and publication keyset             |
| `GET /api/v1/discovery`                   | Global publication/first-seen keyset, source/topic/text/window/cutoff filters                 |
| `GET /api/v1/analytics`                   | Server SQL counts, observed UTC-day coverage, sentiment/source/model distributions and limits |

Router/query support lives in `apps/api/routes/intelligence.py` and
`aegis/intelligence/read_models.py`; contracts in `aegis/contracts/intelligence.py`.
The checked-in OpenAPI export and frontend API types were regenerated using the
repository tooling. Existing API paths/schemas were preserved. New optional
AnalystAdapter ports preserve custom-adapter compatibility; unavailable ports
show honest capability states. Sourced discovery responses avoid full source
registry scans and per-row intelligence fetching. Existing abort signals,
request deadlines, credentials policy and bearer transport remain.

Limits are 1–100 rows, default 25 in the API and 20 from the frontend; model/source
distribution lists cap at 100 and return explicit Other counts. Cursors are bounded
to 32768 characters, freeze `as_of`, include the filter fingerprint and stable last
key, and reject invalid/replayed filter combinations. Relevant SQL statements
have a 5-second timeout. No browser-side corpus aggregation is used.

No migration or index was introduced: representative query measurements did not
justify one. No tables, workers, algorithms or external infrastructure were added.

## Topic Identity and Evidence Policy

Topic IDs encode a versioned, exact tuple of label, provider, model name, model
version and configuration hash using UTF-8 compact JSON/base64url. Labels alone
are not stable identities. Similar text and different model/configuration cohorts
are never silently merged. Strict identity validation handles full supported model
strings and rejects invalid data, including NUL before a PostgreSQL query.

For each document and exact model cohort, select the latest eligible topic analysis
by availability and then analysis ID descending before expanding its outputs.
Only documents created and assessments available by the cutoff participate.
Repeated matching outputs contribute one document; the selected analysis's maximum
matching confidence is exposed as model-reported confidence, not certainty.

Directory and dossier expose actual source attribution, unique cohort document
counts, first/latest selected availability, exact identity, supporting source text,
publication/first-seen dates and loaded assessment details. Supporting reporting
uses paginated publication ordering, unknown publication dates last. Related entity
and event associations are not inferred from topic labels; the directory link is
explicit general navigation. No biography, generated summary, canonical taxonomy,
importance score or relationship graph was manufactured.

## Chronology and Analytics Definitions

Chronology is global server ordering, not a client sort of one returned page:
publication descending, NULLS LAST, then document ID ascending. First Seen is a
separate explicit ordering. Snapshots and filter fingerprints remain stable across
pages. Publication, acquisition, occurrence and model availability retain their
distinct meanings. Discover gives the first chronological record visual emphasis
and explicitly disclaims an importance ranking.

Analytics windows are timezone-aware `[start,end)` intervals of at most 366 days,
with explicit publication or first-seen basis, optional exact topic/source and
availability cutoff. Every displayed count retains this population and snapshot.
Drilldown URLs preserve the same population, basis, interval and cutoff.

| Value                            | Definition                                                                              |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| Documents in Population          | Unique eligible source documents with a known selected-basis time inside the window     |
| Classified Documents             | Documents with an eligible persisted document-level sentiment result                    |
| No Persisted Document Assessment | Population minus classified; no invented inference-failure/abstention reason            |
| Unknown Time Count               | Otherwise eligible documents with missing basis time, outside the dated denominator     |
| Coverage                         | Actual observed UTC days and counts; absent days are not filled or forecast             |
| Sentiment                        | Latest eligible document-level sentiment per document; entity-specific outputs excluded |
| Source Distribution              | Unique documents per recorded source; explicit capped-list Other count                  |
| Model Attribution                | Selected sentiment provider/model/version document counts; explicit Other count         |

Sentiment selection orders eligible document-level assessments by availability and
analysis ID descending; the first matching stored output is used. Entity-specific
sentiment does not count as document sentiment. Neutral/mixed labels remain
separate. Configuration hashes incorporate document context and cannot be used
as a corpus-wide selector; model attribution therefore groups the selected result
by provider/name/version, while exact topic cohorts keep configuration identity.
Stored missing/abstained/unavailable worker outcomes cannot be reconstructed as
separate counts because they are not persisted. These limitations are displayed.
Classifications do not measure public opinion or establish calibrated factual truth.

Historical analysis cutoffs exclude future assessments, but mutable source names,
document prose/metadata and timeless entity associations are not full historical
snapshots. Reports explicitly retain this limitation. An older analysis revision
does not become an independent source article. Mock data derives from existing
fictional records and now validates the same paired/aware/bounded time windows;
revision comparisons use timestamp instants across timezone offsets.

## Media Lab and Licensing Boundaries

Publisher article/image and video-reference sections have independent bounded
cursors. Publication, acquisition, refresh and expiry are displayed from their
actual fields. Attribution and metadata expand without changing external media
into cryptographic evidence. URL validation, no-referrer behavior, lazy images,
aspect ratios and failed-image recovery remain. A refreshed valid URL resets its
previous failure state. Missing or unavailable providers never simulate success
in Real API mode.

The stored-attachment inspector requires explicit document selection and exposes
supported object/hash/subject/input/provenance metadata. No authorized image
delivery/preview contract exists, so stored previews remain unavailable. Remote
publisher images are browser references, not downloaded, mirrored, proxied or
authenticated stored bytes. External video records are metadata and viewing links;
no playback, transcription, OCR or inference service is claimed.

All integration visuals use original CC0 synthetic fixtures. Only reserved demo
image URLs are intercepted to deliver the repository's original demo image or an
intentional failure. API, authorization and verification are real. The captures
and manifest disclose this distinction. No publisher media or paid provider quota
was used. Source Serif 4 and Inter binaries/licenses are unchanged official pinned
assets documented in `apps/web/src/app/fonts/README.md`.

## Isolated Integration and Security Evidence

The task-owned runtime `aegis-completion-20261008-c1600b0` used new loopback
PostgreSQL 35432, Redis 36379, MinIO 39000/39001, Temporal 37233/38233, secured API 38000
and real frontend 33000. PostgreSQL/MinIO used tmpfs; keys, bucket and database were
fresh. The current-source worker ran offline models; provider keys were blank.
No native/user PostgreSQL 5432, shared bucket, existing volume or production endpoint
was selected. Temporary reports and keys stayed in ignored task directories.

The new launcher, product probe and live browser tests verify runtime ownership
before write-capable checks: immutable Docker project/service/container identities,
recorded process executable/argv/creation times, the actual loopback listener,
secure environment seal, owned-key identity and HTTP/SQL sentinel correlation.
Stop rejects PID reuse and foreign containers and never removes volumes.
Acquisition test windows and synthetic expiry derive from persisted times; fixed
publisher dates remain separate. Native Node fetch replaces credential-bearing
Playwright API requests and sanitizes transport errors, avoiding JWTs in failure
call logs. Traces/videos/automatic screenshots are disabled for real credentials.

Supported real journeys cover all ten requested flows. Actual HTTP acceptance
also tests source registration/ingestion and workflow completion, SQL/object
storage, search/similarity, topic/cohort membership, multi-page ordering,
cutoff/aggregate consistency and protected scopes. Explicit verification returned
real content/chain/signature outcomes. Tampered SQL/raw/image records were detected
and restored within the owned runtime. Security audit redaction was exercised.
The secure API was never weakened to make the broad test suite pass; isolated
subprocess test defaults are separate from the running secured API.

An independent reviewer inspected the full sprint and then re-reviewed corrections.
All five established findings—mock window validation, test JWT logging, runtime
write ownership, date-dependent fixtures and ambiguous cohort labels—were resolved.
No additional established high/critical regression remains. Static review is not
represented as a separate live execution or production security certification.

## Measured Performance

Final runtime cleanup was verified at `2026-10-09T05:44:14Z`: all four owned
containers exited successfully, API/worker processes were absent and all seven
owned service ports were closed. Both frontend servers were also stopped. No
container or volume was removed; the task-created Redis volume remains. Disposable
PostgreSQL/MinIO tmpfs was discarded. Two stop attempts failed closed when child
termination also exited its wrapper; a fresh guarded retry completed with exit0.
This retry behavior is a known limitation of the Windows-only test helper,
not a production-service change. The sanitized evidence is
`.test-tmp/completion-runtime/stopped-status.json`.

Fresh browser contexts, three initial-load samples per route, Chromium production
build, unthrottled local machine; OS/server/browser process remain warm. Measurements
include visible-link prefetches. They are laboratory observations, not field CWV,
INP or percentile claims. Mock measurements do not measure provider/API latency.

| Route     | LCP Range | CLS Range         | Encoded JavaScript |
| --------- | --------- | ----------------- | ------------------ |
| Discover  | 424–536ms | 0.000125–0.001001 | 222436bytes        |
| Analytics | 176–192ms | 0.011053–0.015960 | 216112bytes        |
| Media Lab | 176–192ms | 0.000100–0.000125 | 216112bytes        |

Discover's initial CLS was 0.184725–0.185366. A source-level layout-shift observer
identified the media section moving when the archive loaded. Reserving archive
loading space reduced the measured shift to the range above. No screenshot UI was
hidden. Charts use a small SVG; the timed DOM read rounded to 0 ms and is only a
proxy, not isolated React CPU. No eager per-row intelligence was observed in these
initial loads or the dedicated actual API/topic tests.

At 390px, font payload fell from 1,128,028 to 781,340 encoded bytes in all three cold-context
samples: 346,688 bytes (30.7%) saved by omitting the unused desktop italic face. Desktop
still uses all three original fonts (1,128,028 bytes). Further subsetting is deferred
pending language coverage and licensing review; no arbitrary substitute was used.

Representative isolated corpus: 2,006 documents / 8,010 analyses. SQL topics 22.09 ms,
discovery 10.549 ms, analytics 18.761 ms; HTTP 73.08/20.43/27.03 ms respectively. This supports
using existing PostgreSQL without a new index at this scale, not a production SLO.
The five-second statement timeout and bounded result limits remain.

Evidence files under the external visualization root:
`completion-performance-before.json`, `completion-performance.json` and
`completion-mobile-performance.json`. Backend timings were captured in the
focused test's execution output rather than a standalone saved benchmark artifact.
Reproduce with
`tests/integration/test_intelligence_read_models.py::test_representative_sql_population_remains_bounded_with_revisions`:
it seeds a disposable schema, captures actual SQL and measures
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` plus HTTP elapsed time; rerun timings vary.

## Validation Matrix

| Gate                                                | Final Result                                                                                                                                 |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend API generation check                       | Exit0; checked-in types match exported contract                                                                                              |
| Frontend unit/component                             | 68 passed in 14 files                                                                                                                        |
| Next route typegen + TypeScript                     | Exit0, normal generated type reference restored                                                                                              |
| ESLint                                              | Exit0; both generated build directories excluded, no product-rule suppression                                                                |
| Production build                                    | Mock and isolated Real API builds exit0;16 functional routes + not-found                                                                     |
| Full Chromium production suite                      | 105 passed, 8 skipped, 113 total, 1.1m; includes both opt-in performance probes and supported 512-character topic/model regression           |
| Actual API browser journeys                         | 2 passed, 53.0s + 12.3s (1.1m); real API, scopes, verification and 38 mask-free captures                                                     |
| Backend full pytest                                 | 374 passed, 0 skipped, 1 existing Starlette TestClient deprecation warning, 32.00s; includes real web smoke and 23 runtime guard regressions |
| Backend Ruff / Mypy / OpenAPI export check          | Exit0; 246 files formatted, Mypy 119 source files, export check and repository secret guard passed                                           |
| HTTP MVP acceptance / security demo / product probe | 22 checks / 14 checks passed on the owned runtime; final ownership-guarded product repeat 8 groups passed                                    |
| Automated accessibility                             | Axe WCAG 2 A/AA, 2.1 A/AA, 2.2 AA and best-practice: zero violations in 32 route/view checks                                                 |
| Responsive/keyboard                                 | All 16 routes at 1440/1024/768/390/320px; 80 views, expanded panels, focus and Escape                                                        |
| Text/fallback                                       | All 16 routes doubled computed text at 720px; blocked local fonts/mobile navigation passed                                                   |

The eight full-browser skips are: two disposable live cases run separately, native
Chromium zoom (shortcut unsupported in headless), and five opt-in tests targeting
other live/public-safe/historical/provider/volume environments. Those external
environments were not contacted; the new owned-runtime tests cover supported real
journeys without paid acquisition. CSS/doubled text checks do not substitute for
native zoom or screen-reader validation. Backend skips are recorded in the final
result below rather than assumed from the previous 350 passed / 1 skipped checkpoint.

Reproduced and corrected failures: mock frozen-cutoff selection, offset revision
comparison, partial/invalid mock windows, cohort option ambiguity, maximum-length topic heading overflow, missing section
heading, expanded narrow controls/table headers, and generated alternate-build lint
noise. Initial broad backend CORS/OIDC environment conflicts were isolated to the
test subprocess without changing secure service behavior. No screenshot assertion
baseline was silently updated. Existing screenshots are fresh review captures,
not a claim of pixel-equivalence across intentionally redesigned pages.

## Screenshots and Visual Review

External root:
`C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a`.
Actual real API captures live in `completion-live/1440` and `completion-live/390`.
The 38 original full-page files and `capture-records.json` record demo data, viewports,
routes and the disclosed demo-image interception. Tokens are absent without masks.

| Filename in Both Width Folders   | View                                                     |
| -------------------------------- | -------------------------------------------------------- |
| `01-discover.png`                | Discover                                                 |
| `02-story-detail.png`            | Story Detail                                             |
| `03-search.png`                  | Search                                                   |
| `04-expanded-evidence.png`       | Expanded Evidence                                        |
| `05-entity-directory.png`        | Entity Directory                                         |
| `06-entity-intelligence.png`     | Entity Intelligence                                      |
| `07-events.png`                  | Events                                                   |
| `08-topic-directory.png`         | Topic Directory                                          |
| `09-topic-detail.png`            | Topic Detail and Expanded Assessment                     |
| `10-topic-analytics.png`         | Filtered Topic Analytics                                 |
| `11-media-lab.png`               | References, Fallbacks and Stored Metadata                |
| `12-verification.png`            | Actual Authorized Verification                           |
| `13-operations.png`              | Operational Overview                                     |
| `14-sources-ingestion.png`       | Sources, Administration and Known Completed Workflow     |
| `15-provider-controls.png`       | Provider Controls, Read Only                             |
| `16-security-audit.png`          | Server Audit Records                                     |
| `17-chronological-discovery.png` | Chronological Discovery With Expanded Population Filters |

Mobile additionally includes `18-mobile-navigation.png`. The `reflow` folder holds
`analytics-320.png`, `discovery-768.png` and `media-lab-1024.png`, reviewed as actual
rendered screenshots alongside the desktop/mobile series.

Labelled contact sheets: `completion-live/contact-1440-{1,2,3}.png`,
`completion-live/contact-390-{1,2,3}.png` and `completion-live/contact-reflow.png`.
These show opening-view excerpts for legibility; original full pages remain separately
available. Layout checks span the other three requested widths, with automated
axes, keyboard and expanded-state coverage. Final captures are visually reviewed
for the approved typography, spacing, attribution, focus/reflow, long identifiers
and honest image failures. No production publisher screenshots were substituted.
`completion-live/review-index.md` links all seven sheets and all 38 unmodified originals.

## Remaining Limits and Manual Validation

No unresolved critical/high regression is established in the available local
checks. Deferred capabilities remain explicit: authorized stored image delivery,
external video playback/inference, topic-related entity/event aggregation,
canonical topic taxonomy, generated summaries, paid-provider acquisition and
complete historical metadata reconstruction. None is presented as finished.

Before production rollout, manually check native browser zoom at 200% and text-only
zoom on all destinations with long identifiers, charts and expanded panels; verify
NVDA/Firefox or NVDA/Chrome plus VoiceOver/Safari reading order, headings, mode/auth
announcements, table/disclosure labels, selected topic identity and asynchronous
loading/error announcements. Check source-language pronunciation where metadata is
present. Headless keyboard/accessibility-tree/axe checks do not certify those ATs.
Firefox/Safari/iOS rendering and field performance remain outside the Chromium
local run. Larger production SQL populations need deployment-specific plans/SLOs.

## Migration, Rollback and Release Recommendation

No database migration is required. Deploy the additive API/contracts before the
frontend: old clients remain compatible, while new Discover depends on discovery
support. Keep generated contract verification in CI. A coordinated frontend/API
rollback is ordinary Git deployment of the previous version; no data migration,
release-tag rewrite or canonical-record transformation is involved. Older frontend
versions continue using preserved document/search/provenance APIs.

The branch is a local release candidate for owner visual review. Merge readiness
depends on reviewing this complete feature diff against the current intended main
target, current CI and the documented manual browser/AT checks. Follow repository
merge rules: direct fast-forward where possible, otherwise reviewed normal merge;
no rebase/cherry-pick replacement. No merge or deployment has been performed.
Production OIDC, secret management, CORS, paid providers and authorized media
delivery require existing deployment controls and separate owner decisions.

Owner decisions before rollout: approve the complete visual diff; schedule native
zoom/assistive-technology and target-browser checks; coordinate API-before-frontend
deployment and rollback; choose production OIDC/CORS/secret settings through the
existing deployment process; separately authorize paid providers, licensing and
stored-asset delivery if desired. None of those deployment or deferred-product
decisions was exercised automatically in this sprint.

## Complete Changed-File Manifest

58 tracked implementation/documentation paths relative to the sprint baseline:

- `.gitignore`
- `aegis/contracts/intelligence.py`
- `aegis/intelligence/read_models.py`
- `apps/api/main.py`
- `apps/api/routes/intelligence.py`
- `apps/web/e2e/analytics.spec.ts`
- `apps/web/e2e/completion-accessibility.spec.ts`
- `apps/web/e2e/completion-live.spec.ts`
- `apps/web/e2e/completion-performance.spec.ts`
- `apps/web/e2e/discovery.spec.ts`
- `apps/web/e2e/editorial.spec.ts`
- `apps/web/e2e/media-lab.spec.ts`
- `apps/web/e2e/polish.spec.ts`
- `apps/web/e2e/providers.spec.ts`
- `apps/web/e2e/topics.spec.ts`
- `apps/web/eslint.config.mjs`
- `apps/web/next.config.ts`
- `apps/web/package.json`
- `apps/web/src/app/analytics/page.tsx`
- `apps/web/src/app/discovery/page.tsx`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/multimedia/page.tsx`
- `apps/web/src/app/topics/[id]/page.tsx`
- `apps/web/src/app/topics/page.tsx`
- `apps/web/src/components/editorial/masthead.module.css`
- `apps/web/src/components/editorial/masthead.tsx`
- `apps/web/src/components/intelligence/charts.test.tsx`
- `apps/web/src/components/intelligence/charts.tsx`
- `apps/web/src/components/intelligence/intelligence.module.css`
- `apps/web/src/components/intelligence/topic-evidence.test.tsx`
- `apps/web/src/components/intelligence/topic-evidence.tsx`
- `apps/web/src/components/multimedia.tsx`
- `apps/web/src/components/pages/analytics.test.tsx`
- `apps/web/src/components/pages/analytics.tsx`
- `apps/web/src/components/pages/chronological.tsx`
- `apps/web/src/components/pages/discover.module.css`
- `apps/web/src/components/pages/discover.tsx`
- `apps/web/src/components/pages/media-lab.module.css`
- `apps/web/src/components/pages/media-lab.test.tsx`
- `apps/web/src/components/pages/media-lab.tsx`
- `apps/web/src/components/pages/topics.tsx`
- `apps/web/src/lib/api.ts`
- `apps/web/src/lib/generated/api.ts`
- `apps/web/src/lib/intelligence-api.test.ts`
- `apps/web/src/lib/intelligence-fixtures.ts`
- `apps/web/src/lib/models.ts`
- `apps/web/src/lib/queries.ts`
- `apps/web/tsconfig.json`
- `docs/frontend-completion-ledger.md`
- `docs/frontend-completion-report.md`
- `pnpm-lock.yaml`
- `schemas/openapi/v1.json`
- `scripts/completion_integration.py`
- `scripts/completion_product_probe.py`
- `tests/integration/test_intelligence_read_models.py`
- `tests/unit/test_api.py`
- `tests/unit/test_completion_runtime.py`
- `tests/unit/test_intelligence_reads.py`

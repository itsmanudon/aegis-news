# Aegis News frontend

The homepage is an editorial archive-discovery experience. The operational
overview is at `/operations`. News & Intelligence and Operations & Security share
one provider/identity boundary; all existing product URLs remain supported.
Reader and operational styles are scoped separately. Pinned Source Serif 4 and
Inter fonts are served locally; provenance and licenses are recorded in
[`src/app/fonts/README.md`](src/app/fonts/README.md).
Shared capitalization, corner, numeric typography and control rules are recorded
in [Frontend Design Guidance](../../docs/frontend-design-guidance.md).

Run from the repository root:

```sh
pnpm install --frozen-lockfile
pnpm web:dev
```

The console defaults to a clearly labelled fictional workspace and needs no backend services. Set public configuration in `apps/web/.env.local` before starting Next.js:

```dotenv
NEXT_PUBLIC_DATA_MODE=mock
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Use the header's Data mode selector to switch while navigating. The selection lasts for the current app session; a full reload restores the environment default. Switching recreates the TanStack Query client, query observers, mutation state and identity context. Real mode never falls back to fixtures.

## Integrated real mode

Compose builds the console in real mode. Paste a five-minute development token from `scripts/security_dev.py token --key-id local --role admin` into the header. Tokens stay in memory; changing identity destroys the query cache. See [the local MVP runbook](../../docs/mvp-integration.md) for exact commands. Production access tokens come from an external OIDC provider.

Real mode supports documents/intelligence, entities, events, title/text search, live provenance verification, sources, scoped source creation/ingestion, workflow status, and authorized audit reads. Similarity is available through the API. Integrity is unverified until an actual check; feed-wide verified/failed filtering explicitly reports unavailable. Source editing and a production login redirect are deferred.

## Screens

- Discover (`/`): an archive story lead, supporting headlines, attributed source
  excerpts, publication/first-seen metadata, and independent provider-media reads.
  Layout emphasis is not recency or importance ranking. No generated summary,
  topic association, or integrity claim is added to a story preview.
- Operations (`/operations`): loaded-page evidence counts, integrity review queue,
  timeline and document register. Unchecked and failed records both await review;
  they are not counted as confirmed integrity failures.
- Documents/Search: source-first editorial rows, literal excerpts, loaded-page
  counts, shareable filters and opaque cursor pagination. Desktop offers an
  explicit Evidence Table; mobile always uses readable editorial rows. Expanded
  rows reveal already loaded evidence without intelligence requests.
- Story Detail: attributed captured text, publisher link and content extent,
  four-stage timestamps, separate model assessments, linked evidence and a
  compact desktop evidence rail. Detailed mobile evidence follows the reading
  content. Acquisition failures do not hide the primary source report.
- Entities: canonical register, entity detail and associated documents.
- Events: source/model filter; order by occurrence or intelligence availability.
- Provenance: hashes, operation input/subject IDs, signed/unsigned/failed example outcomes.
- Audit/security: simulated identity and role context, audit outcome filtering.
- Sources/admin: read-only registry and explicit administration integration boundary.

In mock mode, all source names, articles, hashes, signatures, models and audit records are fictional. Mock verification returns a typed presentation fixture; it does not perform cryptography. Source facts mean statements attributed to a source, not independently established truth. Model outputs are assessments and confidence is model-reported.

## Architecture and contracts

`src/app` contains thin App Router pages, metadata and route boundaries.
`src/components/pages` owns screen compositions. Shared document table, time rail,
analysis panel and provenance card live in `src/components/documents`.
`src/components/editorial` contains only the masthead, story lead/rows/metadata,
and homepage media composition. Their CSS modules are separate from the existing
evidence/operations styles in `legacy.css`, scoped under `.legacy-content`.
Small semantic primitives remain in `src/components/ui`; no new component framework
is introduced. CSS tokens and Tailwind remain available. Builds need no remote
font service or decorative assets.

`src/lib/queries.ts` owns TanStack Query keys and cancellation. `AnalystAdapter` in `models.ts` is a frontend composition interface, not a proposed server payload. Components only consume this port. `api.ts` centralizes transport, typed errors, request IDs, cancellation and a 10-second real request deadline. `IdentityPort` is the session integration seam: mock mode has a simulated analyst; real mode is anonymous with no invented login, tokens or production permissions.

`scripts/generate-api.mjs` reads `schemas/openapi/v1.json` unchanged and generates
`src/lib/generated/api.ts` using openapi-typescript. The same tool derives
`domain.ts` from checked-in JSON domain schemas by composing an in-memory OpenAPI
3.1 document and resolving local definitions. Backend types are never handwritten.
Fixture compositions use these generated records directly. Verification, audit
and session presentation types compose the current backend responses.

`openapi-fetch` uses generated path types for the registered product, identity,
audit, verification and provider endpoints. Document feeds use one bounded
20-record page without eager per-row intelligence. Full intelligence and
acquisition evidence load through independent queries on document detail; optional
acquisition keeps the same authenticated transport, deadline and cancellation.
Real search uses literal
title/text matching; fixture search additionally matches fictional source/entity
names. Feed-wide verified/failed filtering remains explicitly unavailable in real
mode. Real mode never falls back to fixture success.

`EvidenceDisclosure` uses native details/summary semantics, a labelled region and
Escape-to-close with focus restoration. The optional expanded register uses valid
table rows with a spanning cell and explicit `aria-expanded` buttons. Technical
IDs/hashes stay inside disclosures; source text and model output are distinct.
Filter values (`q`, `source`, `integrity`, `cutoff`), `cursor` and desktop `view`
are restored from the URL. Filter changes clear the cursor; pagination preserves
opaque values. Identity and tokens are never serialized into URLs.
Changing Data Mode clears an adapter-specific cursor while retaining filters;
the existing identity/query-client remount remains intact.

The frontend verification composition retains `contentVerified`, `chainValid`
and `signatureValid` from the existing backend response. Only an explicit check
sets them. `responseReceivedAt` is browser receipt time, not server-attested time.
Mock outcomes are simulated and absent subchecks remain unreported. See the
[Phase 1B handoff](../../docs/frontend-phase1b.md) for decisions, the complete file
manifest, screenshots and validation evidence.

The fixture cutoff is a development demonstration: documents use `first_seen_at`, assessments/events use `available_at`, and entity associations are withheld until document intelligence is available. Publication time may be unknown. Detail pages intentionally open the complete current record and the feed tells analysts this. Production historical guarantees require backend cutoff-bound pagination and association availability; this branch does not claim backtesting support.

## Verification

```sh
pnpm web:api:check
pnpm web:test
pnpm web:typecheck
pnpm web:lint
pnpm web:build
pnpm --filter @aegisnews/web exec playwright install chromium
pnpm web:test:e2e
```

Unit/component tests exercise combined filtering, empty records, knowledge cutoffs, missing IDs, verification outcomes, real-mode isolation, error request IDs, cancellation/deadlines, timestamp normalization and model labels. Playwright exercises major mocked flows, source/security shells, mobile keyboard navigation, unavailable capabilities and connection failures. It intercepts the system endpoint in real-mode tests; no backend branches are needed. CI runs the unit/drift checks through `make check-web`, then installs Chromium and runs Playwright.

For systems with a preinstalled compatible Chromium, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to its executable path. If Windows process cleanup prevents the Playwright-managed Next server from exiting, start a mock Next server on port 3104 yourself and set `AEGIS_E2E_EXTERNAL_SERVER=1` for the test process. The standard Linux/CI command manages its own server. Screenshots/traces go to ignored `test-results`. Optionally set `AEGIS_SCREENSHOT_DIR` to an existing local directory for the reproducible Phase 1B visual-review captures; no golden baselines are updated.

The existing Python stack smoke test checks server-rendered Discover and Operations labels while retaining independent API liveness/readiness checks. That live-stack test still requires its original Compose services; it is separate from the mocked browser suite.

## Integration requirements and deferred controls

1. Product routes are registered and generated. New topic, summary, aggregate,
   discovery-ordering and media-delivery capabilities require separately approved
   contracts. Preserve envelope/request ID/cursor semantics when extending them.
2. Agent 3: supply OIDC session state and server authorization through `IdentityPort`; choose credentials/CSRF behavior from that contract. Current real transport explicitly omits credentials.
3. Real verification and provenance operations use current contracts. Mock
   outcomes remain visibly simulated. Separate content, chain and signature
   results are displayed; a server-attested check timestamp would require an
   approved contract extension.
4. API origin must allow the actual web origin via existing CORS configuration. Only `NEXT_PUBLIC_*` configuration reaches the browser.
5. Source creation, ingestion and manual provider acquisition already exist with
   scoped server authorization. Source editing, users/roles/policies, production
   login flows, authorized media previews/downloads and durable audit export remain
   deferred. Cursor APIs exist; audit/entity/event UI pagination needs further work.
6. No backend ingestion, inference, cryptography, OAuth server, trading, backtesting, Kafka or deployment is implemented.

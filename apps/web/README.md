# AegisNews analyst console

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

## Screens

- Dashboard: evidence counts, integrity review queue, timeline and latest documents.
- Documents: title/text/source/entity search, source and integrity filters, UTC knowledge cutoff.
- Document detail: attributed body, four-stage timestamps, models/confidence/version, entities, events, media metadata, provenance operations and simulated verification.
- Entities: canonical register, entity detail and associated documents.
- Events: source/model filter; order by occurrence or intelligence availability.
- Search: fixture full-text discovery with shared evidence filters.
- Provenance: hashes, operation input/subject IDs, signed/unsigned/failed example outcomes.
- Audit/security: simulated identity and role context, audit outcome filtering.
- Sources/admin: read-only registry and explicit administration integration boundary.

All source names, articles, hashes, signatures, models and audit records are fictional. Mock verification returns a typed presentation fixture; it does not perform cryptography. Source facts mean statements attributed to a source, not independently established truth. Model outputs are assessments and confidence is model-reported.

## Architecture and contracts

`src/app` contains thin App Router pages, metadata and route boundaries. `src/components/pages` owns screen compositions. Shared document table, time rail, analysis panel and provenance card live in `src/components/documents`. Small semantic primitives live in `src/components/ui`, alongside the existing shadcn-compatible aliases, utils and `components.json`. CSS tokens and Tailwind remain available; no remote fonts or visual assets are required.

`src/lib/queries.ts` owns TanStack Query keys and cancellation. `AnalystAdapter` in `models.ts` is a frontend composition interface, not a proposed server payload. Components only consume this port. `api.ts` centralizes transport, typed errors, request IDs, cancellation and a 10-second real request deadline. `IdentityPort` is the session integration seam: mock mode has a simulated analyst; real mode is anonymous with no invented login, tokens or production permissions.

`scripts/generate-api.mjs` reads `schemas/openapi/v1.json` unchanged and generates `src/lib/generated/api.ts` using openapi-typescript. The same tool derives `domain.ts` from checked-in JSON domain schemas by composing an in-memory OpenAPI 3.1 document and resolving local definitions. Backend types are never handwritten. Fixture compositions use these generated records directly. Verification, audit and session presentation metadata are separately declared frontend-only types because these contracts do not yet exist.

`openapi-fetch` uses the generated path types. The only real request currently used is `GET /api/v1/system/info`. Other real adapter methods fail with `CAPABILITY_UNAVAILABLE` without sending requests: the base schema has no registered product endpoints. The UI reports integration pending. No guessed document/search/auth/provenance route is sent.

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

For systems with a preinstalled compatible Chromium, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to its executable path. If Windows process cleanup prevents the Playwright-managed Next server from exiting, start a mock Next server on port 3104 yourself and set `AEGIS_E2E_EXTERNAL_SERVER=1` for the test process. The standard Linux/CI command manages its own server. Screenshots/traces go to ignored `test-results`.

The existing Python stack smoke test now checks server-rendered console labels while retaining independent API liveness/readiness checks. That live-stack test still requires its original Compose services; it is separate from the mocked browser suite.

## Integration requirements and deferred controls

1. Agents 1/2: register product routes in OpenAPI, retain envelope/request ID/cursor semantics, then regenerate types and implement real adapter composition. Agree document/source/analysis/entity/media/event associations and cutoff behavior from actual contracts.
2. Agent 3: supply OIDC session state and server authorization through `IdentityPort`; choose credentials/CSRF behavior from that contract. Current real transport explicitly omits credentials.
3. Agent 3: supply provenance operations and signature/verification result contracts, then replace the frontend verification fixtures. The integrity label and signature/session check are displayed separately.
4. API origin must allow the actual web origin via existing CORS configuration. Only `NEXT_PUBLIC_*` configuration reaches the browser.
5. Source mutation, users/roles/policies, login/logout screens, signed media previews/downloads, durable audit export and cursor-based product pagination await backend capabilities. Source administration is deliberately read-only.
6. No backend ingestion, inference, cryptography, OAuth server, trading, backtesting, Kafka or deployment is implemented.

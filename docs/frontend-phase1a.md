# Editorial foundation — Phase 1A

Phase 1A implements an editorial Discover homepage and two navigational experiences
inside the existing Next.js application. `/operations` retains the operational
overview. Existing documents, entities, events, search, multimedia, provenance,
security and sources routes remain intact.

The baseline was clean `main` at
`49a55e583b93d506d654fe5baf102fed15cc9dc0`, matching local and remote main before
creating `feat/aegis-editorial-foundation`. Baseline validation: API contract check
passed, 16 unit tests passed, and Playwright reported 10 passed / 5 opt-in skips.

## Design and boundaries

- Paper `#F7F6F2`, ink `#17212F`, teal `#0F766E`, dividers `#D6D9D6`, caution
  `#B45353`, supporting text `#57616D`, and white surfaces.
- Locally pinned, unmodified Source Serif 4 and Inter WOFF2 assets from official
  maintainer commits. Their licenses, paths and hashes are in
  `apps/web/src/app/fonts/README.md`. System monospace remains technical typography.
- Editorial CSS modules cover the masthead and homepage. Existing evidence and
  operations styles are retained under `.legacy-content`; their tables/forms are
  not redesigned. Long-form source text adopts Source Serif 4.
- Discover uses the existing bounded `useDocuments` query. It preserves API order,
  explicitly labels archive discovery, and displays source text previews rather
  than generated summaries. Unknown publication times stay unknown.
- The home page's article/video sections use existing adapter methods and query
  keys. They load independently from documents and from each other. Mock mode does
  not fabricate provider-media acquisition. Empty or failed reads retain useful
  navigation. Remote images use the existing URL guard and browser-only loading,
  attribution, no-referrer policy, lazy loading and broken-image fallback.
- One root `Providers` boundary, unchanged adapters/queries and memory-only tokens
  preserve identity/mode cache isolation. Experience navigation changes no scopes.
- No backend contracts, schemas, ingestion, models, crypto algorithms, publisher
  media storage or production authentication are introduced or changed.

## Validation and handoff

Final checks against the production standalone frontend:

| Command / check | Result |
| --- | --- |
| `pnpm web:api:check` | Passed, exit 0; generated API contract unchanged |
| `pnpm web:test` | 4 files / 20 tests passed, exit 0 |
| `pnpm web:typecheck` | Next route type generation and TypeScript passed, exit 0 |
| `pnpm web:lint` | ESLint passed, exit 0 |
| `pnpm web:build` | Next.js 16.3.8 production build passed, exit 0; original routes and `/operations` present |
| `AEGIS_E2E_EXTERNAL_SERVER=1 pnpm web:test:e2e` | Chromium: 21 passed / 5 opt-in skips, exit 0 |
| `pytest -q -p no:cacheprovider tests/e2e/test_status.py` | 1 passed, exit 0, with real frontend SSR and a temporary simulated API liveness service; **not** a live-stack validation |
| Ruff check / format check of `tests/e2e/test_status.py` | Both passed, exit 0 |
| Git staged whitespace check excluding unchanged upstream Source Serif license | Passed, exit 0; full check flags only an upstream trailing space retained verbatim in the license |

Browser coverage includes source attribution, bounded ordering disclosures,
preserved operations/admin routes, mode visibility, synthetic identity changes
and sign-out, 403 recovery, independent media/loading states, empty data, broken
remote images, Escape/focus restoration, keyboard skip navigation and page reflow.
Local font loading is checked through `FontFaceSet`; fallback fonts are checked in
a fresh browser context with WOFF2 requests blocked. Reflow covers 1440, 768, 390
and 320 pixels, plus 300-character source/title/body/provider strings at 320 pixels.

The fresh review reported no Critical findings. Its stale Python smoke assertion
was updated to check Discover and Operations. Long-token overflow was treated as
Important because narrow mobile reflow is an explicit acceptance criterion, and
fixed with CSS scoped to editorial stories and media. Both regressions were
observed failing before the corresponding fixes and passed in final validation.

Rendered screenshots were inspected against the editorial direction. The masthead
and reading grid align, tablet retains a lead/supporting split, mobile stacks in
reading order, and Operations/Documents retain their existing tables and forms.
The mobile menu remains a disclosure with explicit mode and identity context.
The review also corrected masthead width and a responsive text line-break space.
No visual regression baselines were overwritten; temporary reports remain ignored.

Screenshot directory (outside the Git repository):

`C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/`

| Screenshot | Width | Review |
| --- | --- | --- |
| `phase1a-home-desktop.jpg` | 1440 | Editorial homepage, full page |
| `phase1a-home-mobile.jpg` | 390 | Mobile homepage, full page |
| `phase1a-operations-desktop.jpg` | 1440 | Preserved operational overview, full page |
| `phase1a-mobile-navigation.jpg` | 390 | Expanded mobile navigation |
| `phase1a-documents-desktop.jpg` | 1440 | Existing document register, all six fixture records |
| `phase1a-home-tablet.jpg` | 768 | Tablet homepage, full page |
| `phase1a-home-narrow.jpg` | 320 | Narrow mobile homepage, full page |

No application check failures were present in the recorded baseline. Playwright
retains its pre-existing `NO_COLOR` / `FORCE_COLOR` warning. Restricted sandbox
socket access prevented one preliminary Python smoke invocation before it reached
assertions; the same controlled validation completed successfully with local
socket permission. No datasets, volumes, ingestion jobs or live acquisition were
touched. Updating the existing Python SSR smoke test is the only code change
outside the frontend; no backend implementation changes or scope expansion.
The full staged Git whitespace check flags the upstream Source Serif license's
trailing space on line 21; the license is deliberately preserved verbatim.

## Changed-file manifest

```text
apps/web/README.md
apps/web/e2e/console.spec.ts
apps/web/e2e/editorial.spec.ts
apps/web/e2e/evidence.spec.ts
apps/web/e2e/live.spec.ts
apps/web/e2e/providers.spec.ts
apps/web/e2e/volume.spec.ts
apps/web/src/app/fonts/Inter-LICENSE.txt
apps/web/src/app/fonts/InterVariable.woff2
apps/web/src/app/fonts/README.md
apps/web/src/app/fonts/SourceSerif-LICENSE.md
apps/web/src/app/fonts/SourceSerif4Variable-Italic.woff2
apps/web/src/app/fonts/SourceSerif4Variable-Roman.woff2
apps/web/src/app/globals.css
apps/web/src/app/layout.tsx
apps/web/src/app/legacy.css
apps/web/src/app/operations/page.tsx
apps/web/src/app/page.tsx
apps/web/src/components/editorial/discovery-media.module.css
apps/web/src/components/editorial/discovery-media.tsx
apps/web/src/components/editorial/masthead.module.css
apps/web/src/components/editorial/masthead.tsx
apps/web/src/components/editorial/stories.module.css
apps/web/src/components/editorial/stories.test.tsx
apps/web/src/components/editorial/stories.tsx
apps/web/src/components/pages/dashboard.tsx
apps/web/src/components/pages/discover.module.css
apps/web/src/components/pages/discover.tsx
apps/web/src/components/shell.tsx
docs/frontend-phase1a.md
tests/e2e/test_status.py
```

## Known limits and Phase 1B

The normalized document API is not globally newest-first. Home only shows the loaded
page. Full original font coverage is retained (approximately 1.08 MiB of WOFF2
assets); fonts are cached locally, but there is no measured field-performance claim.
Real reads are tested with controlled API responses, not a live authenticated stack.
Five live/corpus/provider/evidence scenarios remain opt-in, avoiding data writes or
external acquisition. Existing feed-wide integrity filtering, eager event/entity
collection loading, and production OIDC redirects remain unchanged.

The recommended Phase 1B entry point is the document reader and responsive search
results: preserve original attribution/content extent, disclose typed assessments
and complete verification checks, and independently load acquisition evidence.
Topic aggregation, summaries, streaming and route migration remain separate work.

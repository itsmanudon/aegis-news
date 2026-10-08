# Phase 1A.1 — Visual Consistency and UI Polish

This pass continues `feat/aegis-editorial-foundation` from the verified, clean
Phase 1A commit `49c63414b0486bae3e884b6391e0b12a9a286580`. It preserves the
editorial layout, existing routes, Paper/Ink/Teal palette and established data
behavior. No Phase 1B, backend, schema, ingestion, model, crypto, dependency,
authentication, adapter or query-layer changes are included.

## Changes

- `apps/web/AGENTS.md` now persists the owner's Title Case preference outside the
  unchanged generated Next.js block. [Shared guidance](frontend-design-guidance.md)
  records typography, tokens and control behavior. Static interface headings,
  navigation, actions and labels use Title Case. Source headlines/body, canonical
  names, model-provided text and identifiers remain unchanged; explanatory prose
  remains sentence case. CSS uppercase/capitalize transformations are removed.
- Shared corner tokens: small 6px, control 10px, panel 12px, overlay 16px and pill
  999px. Controls and existing operations containers use their corresponding
  tokens. Editorial story rows remain unenclosed. The overlay token is reserved;
  no speculative overlay component is introduced.
- Shared `Timestamp` now renders aligned date/clock groups in Inter, with UTC
  normalization and exact ISO `datetime`/`title` attributes. Nonzero seconds and
  milliseconds remain visible. Missing and invalid times remain Unknown. Stories
  and media reuse this component instead of a duplicate story formatter.
- Metrics, dates, clocks and pagination use Inter with tabular/lining numerals.
  Hashes, code, IDs and machine diagnostics retain system monospace. Counts and
  calculations are unchanged; unchecked records remain records awaiting review.
- Navigation hover changes color without text underlines. Each current tab keeps
  one 2px teal border; keyboard focus retains a separate teal outline.
- Data Mode remains a native select with 44px height, shared control radius,
  neutral surface and a local SVG indicator. Forced-colors mode restores the
  native indicator. Handlers, mock/real distinction and identity visibility are
  unchanged.
- Documents/Search filters use warm `#F1F0EB`, aligned white controls and matching
  heights. Desktop exposes all advanced fields. Mobile retains the primary text
  field, Reset Filters and a keyboard-accessible Advanced Filters button whose
  count reflects active source/integrity/cutoff controls. Closing it preserves
  values. Existing UTC cutoff, filtering and cursor behavior are unchanged.
- Operations panels, tables and badges share the neutral surfaces and radii.
  Explicit Verified, Failed, Unverified and Unavailable labels remain distinct.
  Failed badge contrast improved from 4.11:1 to 4.88:1 by retaining the caution
  color on a white surface with a caution border. State and verification semantics
  are unchanged.

## Validation

| Command/check | Exact result |
| --- | --- |
| `pnpm.cmd web:api:check` | Passed, exit 0; generated contract unchanged |
| `pnpm.cmd web:test` | 4 files, 20 tests passed, exit 0 |
| `pnpm.cmd web:typecheck` | Next route type generation and TypeScript passed, exit 0 |
| `pnpm.cmd web:lint` | Passed, exit 0 |
| `pnpm.cmd web:build` | Next.js 16.3.8 production build passed, exit 0 |
| `AEGIS_E2E_EXTERNAL_SERVER=1 pnpm.cmd web:test:e2e` | Final production Chromium run: 26 passed, 5 opt-in skipped, exit 0 |
| Python SSR smoke `pytest -q -p no:cacheprovider tests/e2e/test_status.py` | 1 passed, exit 0; real production frontend with isolated simulated API liveness responses, not a live-stack run |
| Ruff lint and format checks on the updated Python smoke test | Passed, exit 0 |
| Git whitespace checks | Passed, exit 0 |

The existing unit baseline passed before changes. Timestamp grouping, navigation
hover and status contrast regressions were observed failing before their fixes.
Browser coverage now includes the native mode control, visible focus, mobile
disclosure keyboard activation, count/reset/cutoff behavior, numeric typography,
and status contrast. Discover, Documents, Search and Operations were checked for
page overflow at 1440, 768, 390 and 320 pixels. Existing tests continue to cover
mock/real cache isolation, synthetic identity changes/sign-out, permission errors,
empty/loading states, local and fallback fonts, and long unbroken source strings.

A fresh read-only review found no Critical, Important or Minor code issues.
Final screenshots were inspected, including the corrected Failed badge. The
browser review reported no console errors. The task-owned production server was
stopped and browser viewport restored. No screenshot baselines were overwritten.

## Screenshots

All files are outside Git in:

`C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/`

| Required screenshot | Width | File |
| --- | --- | --- |
| Desktop Discover | 1440 | `phase1a1-discover-desktop.jpg` |
| Mobile Discover | 390 | `phase1a1-discover-mobile.jpg` |
| Documents with filters visible | 1440 | `phase1a1-documents-desktop.jpg` |
| Expanded mobile Documents filters | 390 | `phase1a1-documents-mobile-filters.jpg` |
| Desktop Operations | 1440 | `phase1a1-operations-desktop.jpg` |
| Expanded mobile navigation | 390 | `phase1a1-mobile-navigation.jpg` |

Additional reviewed captures: `phase1a1-discover-tablet.jpg`,
`phase1a1-discover-narrow.jpg`, `phase1a1-documents-mobile-collapsed.jpg`,
`phase1a1-documents-narrow-filters.jpg`, `phase1a1-operations-tablet.jpg`,
`phase1a1-operations-narrow.jpg`, `phase1a1-search-tablet.jpg` and
`phase1a1-search-narrow.jpg`. Some full-page capture attempts produced incomplete
frames or failed; final Documents/Operations deliverables were recaptured as
complete viewport images and visually inspected.

## Remaining Limits

Live provider, corpus, ingestion and authenticated backend workflows remain
opt-in and were not exercised. Their selectors were updated for the new interface
capitalization. The controlled SSR check does not establish backend health.
Production OIDC and unsupported real-mode feed integrity filtering are unchanged.
No new topic APIs, summaries or media services are implied.

Operational tables keep their existing internal horizontal scroll at narrow
widths; no page-level overflow was observed. This is a polish pass, not a table or
reader architecture rewrite. Native dropdown/date-picker rendering varies by
browser and operating system; validation used Chromium. No field-performance
claim or font asset/subsetting change is made. The pre-existing Playwright
`NO_COLOR` / `FORCE_COLOR` warning remains.

The branch is ready for the owner's visual review. No merge, deployment or Phase
1B work is authorized by this handoff.

## Changed Files

Complete manifest (41 files; most existing-view changes are interface capitalization):

```text
apps/web/AGENTS.md
apps/web/README.md
apps/web/e2e/console.spec.ts
apps/web/e2e/editorial.spec.ts
apps/web/e2e/evidence.spec.ts
apps/web/e2e/historical-corpus.spec.ts
apps/web/e2e/live.spec.ts
apps/web/e2e/polish.spec.ts
apps/web/e2e/providers.spec.ts
apps/web/e2e/volume.spec.ts
apps/web/src/app/globals.css
apps/web/src/app/legacy.css
apps/web/src/components/documents/analysis-panel.tsx
apps/web/src/components/documents/document-table.tsx
apps/web/src/components/documents/feed.tsx
apps/web/src/components/documents/presentation.test.tsx
apps/web/src/components/documents/provenance-card.tsx
apps/web/src/components/documents/time-rail.tsx
apps/web/src/components/editorial/discovery-media.module.css
apps/web/src/components/editorial/discovery-media.tsx
apps/web/src/components/editorial/masthead.module.css
apps/web/src/components/editorial/masthead.tsx
apps/web/src/components/editorial/stories.module.css
apps/web/src/components/editorial/stories.test.tsx
apps/web/src/components/editorial/stories.tsx
apps/web/src/components/multimedia.test.tsx
apps/web/src/components/multimedia.tsx
apps/web/src/components/pages/dashboard.tsx
apps/web/src/components/pages/discover.module.css
apps/web/src/components/pages/discover.tsx
apps/web/src/components/pages/document-detail.tsx
apps/web/src/components/pages/entities.tsx
apps/web/src/components/pages/events.tsx
apps/web/src/components/pages/provenance.tsx
apps/web/src/components/pages/security.tsx
apps/web/src/components/pages/sources.tsx
apps/web/src/components/provider-admin.tsx
apps/web/src/components/ui/console.tsx
docs/frontend-design-guidance.md
docs/frontend-phase1a1.md
tests/e2e/test_status.py
```

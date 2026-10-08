# Phase 1B — Editorial Reading and Discovery

Implemented on `feat/aegis-editorial-foundation`, starting from clean Phase 1A.1
HEAD `32315d9e62e5e1e52f3cf01d1365dc54942461ae`. Local `main`, `origin/main`
and the verified remote main were `49a55e583b93d506d654fe5baf102fed15cc9dc0`.
The existing feature branch was retained as explicitly requested. No merge,
push, deployment, history rewrite or release-tag operation was performed.

The separate boundary commit is
`367dc1a5b7bc127c2a24ed2d4b5f7b233fa7da77` — acquisition isolation and lossless
verification composition. The implementation/test commit is
`b324cec8630a5d4c3511f8e2c7d1d41f5f20e1ff`. The documentation handoff commit is
discoverable with `git log --oneline 32315d9..HEAD`; the delivery message records
final HEAD.

## Delivered Experience

Story Detail leads with the original headline, source attribution, aligned
Publication/First Seen metadata, truthful captured-content extent and a guarded
publisher article link when available. A source registry URL is labelled Open
Source Address instead of being presented as the article. Source Serif 4 carries
the reading text with a comfortable measure; Inter carries UI and metadata.
Existing pinned local font assets and licenses are unchanged.

Source Reporting remains an attributed statement. Models are separate compact
sections with actual output labels, confidence (including zero), scores, model
name/version and availability. Matching extraction spans validate Unicode
character offsets and surface text; model-reported extraction evidence stays
attributed. Raw configuration hashes, IDs and references live in Technical
Metadata disclosures. No summary, decision explanation or calibrated factual
certainty is manufactured.

The desktop reader has a compact evidence rail beside reporting. Mobile retains
attribution and a short evidence summary near the headline; detailed evidence
follows reporting, assessments and linked evidence in logical DOM order. Stored
attachment metadata and remote provider references are distinct. Acquisition
loading/error/retry does not hide an available source report.

Documents and Search default to editorial rows: source, headline, literal
excerpt, aligned timestamps and actual availability. A separate Story Detail
link remains usable when evidence is collapsed. Expansion reveals only already
loaded excerpts, ingestion/assessment times, model labels/confidence and check
state; no per-row intelligence, acquisition or verification request is made.
Real list data remains explicitly incomplete until Story Detail is opened.

Desktop retains an explicit Evidence Table with valid expanded `tr/td` structure,
six-column spanning regions and semantic buttons. Mobile displays editorial rows
even when the URL retains the table preference. Native disclosures use associated
labelled regions, chevrons, keyboard activation, visible focus and Escape-to-close
with focus restoration. Expanded evidence surfaces are white, restrained and
12px rounded. There are no new animations, gradients, shadows or UI frameworks.

Warm-neutral filters preserve supported source/integrity/UTC cutoff semantics.
URL state restores `q`, `source`, `integrity`, `cutoff`, opaque `cursor` and
desktop `view`; filter changes clear the cursor. Pagination pushes bounded
cursor history and offers First Page rather than an invented previous cursor.
Mode changes clear adapter-specific pagination while preserving filters and the
existing identity/query-cache remount. Counts identify records on this page,
never corpus totals. Unsupported real verified/failed options are disabled;
unsupported direct URLs produce the existing typed capability error.

Authored headings/labels use Title Case; source headlines and model labels keep
their original capitalization. Mobile navigation is more compact while retaining
44px controls, one active indicator, visible mode and identity. The mock Discover
multimedia empty state explains actual provider records and external references
without fictitious images or videos.

## Frontend Composition and Contract Changes

Backend OpenAPI/domain schemas, endpoints, authorization, inference, ingestion
and cryptography are unchanged. The existing `AnalystAdapter` gains optional
`acquisition(id, signal)` using the existing acquisition endpoint. The primary
`document` method no longer waits for this optional request. `useAcquisition`
uses a mode-scoped document key, the existing authenticated client, typed errors,
request IDs, cancellation and 10-second transport deadline. Mock records keep
their existing optional composition; no provider acquisition is fabricated.

The frontend `Verification` composition replaces misleading `checkedAt` with
`responseReceivedAt` and retains existing backend `content_verified`,
`chain_valid` and `signature_valid` as separate booleans. Overall `valid` still
determines the overall result. UI labels Content Integrity, Chain Validity and
Digital Signature separately, retaining mixed failure/success outcomes. The local
time is explicitly Response Received At, not server-attested verification time.
No subchecks are invented for the simulated adapter. Real records remain
unchecked until an explicit action returns; hashes/signatures never establish
factual truth. The reader shares one visible mutation result and aborts checks
on record unmount/change; mode/identity changes preserve the existing isolation.

## Component Composition

```text
Existing Providers / Identity Boundary / Shell / Masthead
├─ Feed (Suspense → URL-Driven DiscoveryFeed)
│  ├─ Existing Warm Filters / Active Filters / Page Count
│  ├─ EditorialResults → StoryMetadata / EvidenceDisclosure → EvidenceDetails
│  └─ Optional DocumentTable → Valid Expanded EvidenceDetails Rows
└─ DocumentDetail → Keyed StoryReader
   ├─ Headline / StoryMetadata / Extent / Source Link / Evidence Summary
   ├─ Source Reporting → Captured Paragraphs
   ├─ AnalysisPanel → Actual Outputs / Technical Metadata Disclosures
   ├─ Linked Entity / Event / Attachment Disclosures
   └─ Evidence Rail → TimeRail / ProvenanceCard / Acquisition / Record Metadata
      └─ Shared useVerification → VerificationDetails
```

Existing URLs are retained. `/documents/[id]` has Story Detail metadata;
`/documents` and `/search` share the new result composition. Discover,
Operations, entities, events, multimedia, verification, security and sources
remain within the same application and shared authorization boundary.

## Validation

| Command / Gate | Result |
| --- | --- |
| `pnpm web:api:check` | Passed; generated contracts unchanged |
| `pnpm web:test` | 27 passed, 5 test files |
| `pnpm web:typecheck` | Passed, exit 0 |
| `pnpm web:lint` | Passed, exit 0 |
| `pnpm web:build` | Passed, all existing routes retained |
| `AEGIS_E2E_EXTERNAL_SERVER=1 pnpm web:test:e2e` | 40 passed, 5 opt-in skipped; 45 total, exit 0 |

Production standalone ran on `127.0.0.1:3104` with mock environment default.
Controlled Real API browser routes exercise actual adapter contracts without
touching user datasets. Coverage includes optional 403/cancellation, loading and
empty acquisition, 401/403 failures, mixed verification subchecks, absent models,
headline-only capture, unknown publication times, real unsupported integrity,
query limits and opaque cursors, restored URL/reset behavior, mode/identity
isolation, source article attribution and long titles/hashes/model names.

Pointer and keyboard tests cover native evidence rows, Enter, Escape, focus
restoration and visible focus; table regions remain valid and scrollable. Reflow
was checked at 1440, 1024, 768, 390 and 320px, plus 720 CSS pixels as the 1440px
at 200% layout equivalent and CSS magnification at 200%. This is not a claim of
manual browser-menu zoom testing. Existing fallback-font, navigation, operational
and security regression coverage is preserved. No screenshot baseline was
silently updated.

Baseline unit tests passed (20 before Phase 1B); no existing baseline application
failure was found. Migrated test-flow failures and review findings were fixed.
Five tests remain opt-in: live MVP, historical corpus, provider integration,
real volume and public-safe evidence capture. They were not executed because
their backend/data/token prerequisites were not launched. Shared reader actions
used by live tests are covered against safe mock records in the default suite.
No backend/Docker/data-reset operation was performed. Browser color-environment
warnings and Git line-ending notices are non-failing environment output.

## Screenshots and Visual Review

All final PNGs were captured by `e2e/visual-review.spec.ts` against the production
build with loaded local fonts and inspected. These are visibly fictional mock
records. Files are outside Git in:

`C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/`

| Capture | File | Width |
| --- | --- | --- |
| Desktop Story Detail | [phase1b-story-desktop.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-story-desktop.png) | 1440 |
| Evidence Rail / Expanded Technical Metadata | [phase1b-story-evidence-expanded.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-story-evidence-expanded.png) | 1440 |
| Mobile Story Detail | [phase1b-story-mobile.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-story-mobile.png) | 390 |
| Narrow Story Detail | [phase1b-story-narrow.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-story-narrow.png) | 320 |
| Desktop Documents, Collapsed | [phase1b-documents-desktop-collapsed.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-documents-desktop-collapsed.png) | 1440 |
| Desktop Documents, Expanded | [phase1b-documents-desktop-expanded.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-documents-desktop-expanded.png) | 1440 |
| Mobile Documents, Collapsed | [phase1b-documents-mobile-collapsed.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-documents-mobile-collapsed.png) | 390 |
| Mobile Documents, Expanded | [phase1b-documents-mobile-expanded.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-documents-mobile-expanded.png) | 390 |
| Desktop Expanded Evidence Table | [phase1b-evidence-table-expanded.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-evidence-table-expanded.png) | 1440 |
| Desktop Filtered Search | [phase1b-search-desktop.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-search-desktop.png) | 1440 |
| Mobile Search / Advanced Filters | [phase1b-search-mobile-filters.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1b-search-mobile-filters.png) | 390 |

Captures start at the top after interactions to avoid full-page fixed-element
composition artifacts; accessibility elements are not hidden or edited out.
The result retains Paper/Ink/Teal, warm controls, serif headlines, unenclosed
stories and restrained white evidence surfaces. Narrow text and technical values
wrap without editorial page overflow. The capture script is reproducible with
`AEGIS_SCREENSHOT_DIR` or falls back to ignored Playwright output.

## Review, Decisions and Remaining Limits

One fresh reviewer inspected the entire Phase 1B range and working tree. Its
Important findings were incompatible mode cursors and stale live reader
selectors; the unsupported Pending label was regraded Important. All entered
one regression-led fix pass. No second review was substituted for verification.
The cursor and historical table tests first reproduced the failures; the shared
live actions first failed with duplicate model metadata and obsolete attachment
markup. All four regressions now pass in the 40-test default browser suite.
The first post-fix run exposed an incorrect test count: literal `Port` also
matches `report`, so three mock records are expected. Correcting that oracle
preserved the actual substring-search contract; no fixture or API was changed.

Decisions made during implementation:

1. Keep the explicitly requested current feature checkout; no new worktree or
   branch. This retains the approved Phase 1A.1 baseline.
2. Use native Next.js History integration and URL source of truth under Suspense.
   Filter changes replace history, pagination pushes it; cost: keystroke history
   is not individually navigable. Dense-view preference persists on mobile while
   mobile rendering uses editorial rows.
3. Preserve only known enum labels through explicit mapping. Unknown machine
   identifiers and publisher/model content remain untouched; unfamiliar labels
   may be technical rather than polished.
4. Do not persist mode/identity through hard reloads: existing environment default
   remains authoritative. Filter URLs restore state, not authentication.
5. Expand loaded evidence only; list records lacking intelligence link to full
   detail. Cost: real archive expansions cannot show assessments not supplied by
   their endpoint. Optional acquisition is separate from primary intelligence.

Deferred review minors: event-extraction `occurred_at` and entity-extraction
`predicted_kind` are not yet exposed in the assessment panel (an existing output
presentation gap); compact model output strips retain the small 6px radius,
while expandable detail surfaces use the specified 12px radius.

No API guarantee exists for complete article content, global newest-first order,
corpus totals, backward cursors or server-attested check time. Unknown or absent
data remains unavailable/unconfirmed. Existing eager source-registry pagination
is unchanged; document reads remain bounded with no eager per-row intelligence.
Source-only URLs cannot identify an original article. Remote media can fail,
remain external references and carry no stored-asset integrity claim. Live
backend/assistive-technology and native browser zoom checks remain owner-side
validation limits before integration.

Proposed Phase 1C: bring entity/event browsing and the verification workspace
into this editorial/evidence language using confirmed existing contracts, with
bounded navigation and consistent availability states. Optional model-field
presentation refinements can be included there. Topic aggregation, multimedia
backend work, authentication expansion and deployment require separate approval.
Phase 1C has not started. Return this branch for visual review before integration.

## Complete Phase 1B Changed-File Manifest

Paths below include the boundary commit, implementation, tests and handoff,
relative to the repository root. No backend, generated schema, dependency,
font-asset or license file changed.

```text
apps/web/README.md
apps/web/e2e/console.spec.ts
apps/web/e2e/editorial.spec.ts
apps/web/e2e/evidence.spec.ts
apps/web/e2e/live.spec.ts
apps/web/e2e/polish.spec.ts
apps/web/e2e/reader-actions.ts
apps/web/e2e/reading.spec.ts
apps/web/e2e/visual-review.spec.ts
apps/web/e2e/volume.spec.ts
apps/web/src/app/documents/[id]/page.tsx
apps/web/src/app/legacy.css
apps/web/src/components/documents/analysis-panel.module.css
apps/web/src/components/documents/analysis-panel.tsx
apps/web/src/components/documents/document-table.tsx
apps/web/src/components/documents/editorial-results.module.css
apps/web/src/components/documents/editorial-results.tsx
apps/web/src/components/documents/evidence-details.tsx
apps/web/src/components/documents/feed.module.css
apps/web/src/components/documents/feed.tsx
apps/web/src/components/documents/provenance-card.tsx
apps/web/src/components/documents/use-verification.ts
apps/web/src/components/documents/verification-details.tsx
apps/web/src/components/editorial/discovery-media.module.css
apps/web/src/components/editorial/discovery-media.tsx
apps/web/src/components/editorial/masthead.module.css
apps/web/src/components/pages/document-detail.module.css
apps/web/src/components/pages/document-detail.tsx
apps/web/src/components/providers.tsx
apps/web/src/components/ui/console.tsx
apps/web/src/components/ui/evidence-disclosure.module.css
apps/web/src/components/ui/evidence-disclosure.tsx
apps/web/src/lib/adapter.test.ts
apps/web/src/lib/api.ts
apps/web/src/lib/models.ts
apps/web/src/lib/queries.ts
apps/web/src/lib/source-presentation.test.tsx
apps/web/src/lib/source-presentation.ts
docs/frontend-design-guidance.md
docs/frontend-phase1b.md
```

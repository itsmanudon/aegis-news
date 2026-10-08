# Phase 1D — Operations and Security Experience

Implemented on `feat/aegis-editorial-foundation` from the clean, expected
Phase 1C HEAD `06271b2836b208e9f3e1019629823cc13c72c4f2`.
Local main, origin/main and the inspected remote main remain
`49a55e583b93d506d654fe5baf102fed15cc9dc0`; no remote feature head was found.
The final commit SHA is reported in the delivery message; this document is part
of that commit. Discover, Story Detail and Phase 1C research screens remain intact.
No merge, push, deployment, tag changes, history rewrite or user dataset changes
occurred. Root/frontend AGENTS and installed Next.js 16 client/CSS guidance were
read before implementation.

## Delivered Experience

The source registry is a bounded ledger with source name, actual type, validated
HTTP/HTTPS address and creation time. IDs and schema versions use native Source
Details disclosures. It has loaded-page counts, First Page/Next Page navigation
and separate loading, empty and permission/error states. It does not infer health,
ownership, editing or ingestion history.

Create Source and Submit Articles are separate action forms below browsing.
Labels, field descriptions, validation and disabled pending controls explain the
existing scope requirements. New sources invalidate registry/attribution queries
and become selectable in the current session. The submission selector includes
the loaded registry page and retains the selected source while browsing pages.

Captured plain text supports one article or an explicitly assembled batch of
1–20. Titles, nonempty text/keys, distinct batch keys, decoded UTF-8 content
(256 KiB per article) and encoded request bounds (768 KiB) are checked before
submission. Keys/content remain in place after failures; retries are deliberate.
Media attachments are not added by this form. Language remains the existing
manual text submission's English value; this phase adds no language inference.

A submission response confirms acceptance only. Every returned workflow reference
remains inspectable. A failed repeat retains all previous accepted references,
labelled Previous Accepted Response. Known Workflow presents the actual reported
status, scalar result metadata, document link when supplied and optional reported
error. Raw JSON remains in Workflow Technical Details. Missing/unknown status
stays unavailable. No global pipeline discovery, fabricated timing or polling
is introduced.

Provider Operations separates Configuration Present/Missing from the existing
GDELT Keyless Capability Available. Neither is health. Provider/query/item/geography
controls issue explicit bounded acquisition with `retry_failed: false`.
Known Provider Run lookup is an independent explicit read. Structured run
timestamps/outcomes/counts and workflow references precede raw disclosures.
Acquisition Completed requires supported finished-run evidence and is separate
from Workflow Running/Completed. Provider status unknown and authorization failures
remain visible. No hidden paid calls, acquisition retries or status refresh loop
runs. Query reads retain the existing shared query policy.

Security & Audit separates current identity/roles/scopes, navigation to the
authorized Verification workspace and bounded audit history. The table preserves
exact supplied action/outcome strings, UTC occurrence time, event ID, actor/subject
hashes and request ID. Missing hashes are Not Supplied, not invented anonymous
principals. Page-local outcome filtering is explicitly labelled. A success is
never rewritten as Access Allowed, nor failure as Access Denied. Mock identity
and audit remain visibly simulated.

## Design and Component Structure

Retained pinned Source Serif 4 for page headings, Inter for controls/data and
system monospace for technical evidence. Paper, Ink, Teal and warm-neutral tokens
remain unchanged. Scoped operations CSS supplies compact aligned tables, quiet
rules, white action surfaces, 10px controls and 12px inner disclosures. No new
framework, font download, gradients, exaggerated shadows or animation.

Tables retain semantic rows/cells/headers on desktop and become labelled compact
records below 600px. Source/action and identity/security sections stack below
800px. Provider fields reduce to two columns at 1024px and one on narrow mobile.
Technical disclosure metadata stacks by 1024px; identifiers/raw JSON wrap.
The known-run field/action stays aligned on desktop and stacks on mobile.

```text
Existing Shared Providers / Identity / Shell
├── /operations → Dashboard + OperationsNav (existing overview preserved)
├── /sources → Sources + OperationsNav
│   ├── #registry → Bounded Source Table + EvidenceDisclosure + CursorPager
│   ├── SourceAdministration
│   │   ├── SourceCreation
│   │   ├── ArticleSubmission → Returned References + EvidenceDisclosure
│   │   └── #workflow-lookup → WorkflowLookup → WorkflowStatus
│   └── #provider-operations → ProviderAdmin → ProviderRunDetails
└── /security → Security + OperationsNav
    ├── Session Context + Authorization Scopes Disclosure
    ├── Security Operations → Existing /provenance
    └── Audit History → Exact Outcomes + EvidenceDisclosure + CursorPager

Shared operations: useOperation, OperationError, operations.module.css
Shared existing primitives: Button, QueryState, Timestamp, EvidenceDisclosure
```

All existing URLs remain supported; sections do not imply additional backend
routes. Operational Workspaces links distinguish overview, sources/ingestion,
provider operations and security/audit. Existing masthead/identity boundaries,
in-memory tokens, sign-out and query-client remount isolation remain.

## Reused Contracts and Adapter Changes

| Capability | Existing API and Authorization | Frontend Behavior |
| --- | --- | --- |
| Source registry | GET /api/v1/sources, sources:read | One 20-record cursor page, exact source metadata |
| Source creation | POST /api/v1/sources, sources:write | Explicit generated SourceCreate; no fetching |
| Text submission | POST /api/v1/ingestions, ingestions:write | 202 workflow_id only; acceptance separate from completion |
| Batch submission | POST /api/v1/ingestions/batch, ingestions:write | Generated BatchRequest; preserve all submission references |
| Known workflow | GET /api/v1/ingestion-runs/{workflow_id}, documents:read | Explicit reported state/result lookup |
| Provider configuration | GET /api/v1/providers, sources:write and ingestions:write | Credentials/keyless availability, not health |
| Provider acquisition | POST /api/v1/providers/{provider}/fetch or /fetch-all, same two scopes | Explicit bounded request; no client idempotency or automatic retry |
| Known provider run | GET /api/v1/provider-runs/{run_id}, same two scopes | Actual run/outcomes/workflow statuses; no run discovery |
| Audit | GET /api/v1/security/audit, audit:read | 20-record opaque cursor pages, exact raw outcome/reference semantics |

`AnalystAdapter.sourcePage(signal?, cursor?)` and SourceList add bounded registry
browsing while preserving existing `sources()` composition for document attribution.
`audit(signal?, cursor?)` now returns AuditList with nextCursor, raw AuditEvent and
requestId; outcome is the API string rather than a fabricated access decision.
Mock adapters page existing fixtures and do not simulate successful operational
writes. Query keys include mode and cursor; identity/mode remount still isolates
all data and operation state.

The optional `ingestBatch` method uses the existing generated BatchRequest.
Optional AbortSignal parameters were added to source/ingestion/provider writes
and known-run reads. Early abort checks avoid starting cancelled actions.
Existing bearer transport, credentials omission, 10-second deadline, envelope
and typed request errors remain. `useOperation` adds a synchronous duplicate
guard, pending/error state and abort on unmount. There is no automatic mutation
retry. Client scope gating supplements server authorization rather than replacing
it. Generated API/domain files, backend endpoints/schemas, ingestion workers,
models and cryptography were not modified.

Write network/timeouts and 5xx responses conservatively show Request Outcome
Unknown: the server may have acted before the response was lost. Source creation
guidance asks the operator to inspect the registry; provider guidance explains
acquisition may already have started and a repeat can consume quota. Ingestion
guidance preserves source/content/keys for an unchanged retry. Definitive
authorization rejections retain Request Failed, code and request ID.
No client action can guarantee cancellation of work already accepted by the server.

## Validation

All commands run from apps/web; gates use the production standalone frontend on
loopback port 3104 for browser validation.

| Check | Final Result |
| --- | --- |
| pnpm api:check | Exit 0; no generated contract drift |
| pnpm test | 45 passed, 9 files passed, 0 failures |
| pnpm typecheck | Exit 0; route generation and TypeScript passed |
| pnpm lint | Exit 0 |
| pnpm build | Exit 0; Next.js 16.3.8, all existing routes retained |
| Full production Playwright | 75 tests: 69 passed, 6 skipped, 0 failures |
| Three focused review regressions | 3 passed, 0 failures |
| Final external screenshot capture | 1 passed; 36 PNGs captured |

Phase 1D has 15 operational browser cases plus the visual capture case. Coverage
includes bounded source/audit requests and opaque cursor preservation, source
creation and native field validation, synchronous duplicate prevention, batch
keys/returned references, acceptance versus reported state, missing/failed
workflows, credential/keyless configuration, provider 403, audit exact outcomes,
mock/real isolation, expiry/sign-out cancellation, field descriptions, keyboard
disclosures/Escape/focus and desktop lookup alignment. Unit/component regressions
cover bytes/bounds/keys, missing status, URL safety, workflow presentation, request
uncertainty, scope rejection and generated transport payload/cancellation.

Five opt-in live integrations were intentionally skipped: live MVP, historical
corpus, provider evidence, volume and public-safe live evidence. No write-enabled
live backend tests, real acquisitions, real tokens or user dataset operations
were run. Operational browser tests intercept every backend request and use
controlled generated-contract-shaped records. The sixth skip is the inherited
native zoom probe: headless Chromium did not apply its keyboard zoom shortcut.
True per-element 200% text sizing from original computed sizes and five-width
reflow checks still pass; this is not a claim that native zoom was validated.
No existing screenshot golden baseline was updated.

Pre-fix regressions were observed failing: one unit uncertainty test and three
browser cases for uncertain writes, retained accepted references and desktop
lookup alignment. They now pass. An interrupted production run during temporary
standalone asset staging was infrastructure setup, not a product failure; folder
layout was corrected before the final passes. Earlier temporary browser artifact
collisions were resolved by serializing test invocations. Final gates have no
known failing tests.

## Screenshots and Visual Review

36 captures at desktop 1440px, tablet 768px and mobile 390px are stored outside
Git. All twelve categories were inspected across those sizes. Automated long
record/reflow checks additionally cover 1024px and 320px. Capture framing was
corrected to fit sections and wait for loaded overview data; fixed navigation
and development overlays are not hidden to manufacture screenshots.

Except navigation's visibly labelled Mock Workspace, the captures exercise
Real API presentation against intercepted synthetic responses. They are not
live operational evidence. Expanded source/workflow/provider/audit disclosures
are shown; status, failure and empty states remain readable. Provider acquisition
is explicitly shown completed while its submitted workflow remains running.

| View | 1440px | 768px | 390px |
| --- | --- | --- | --- |
| Source Registry | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-registry-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-registry-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-registry-mobile.png) |
| Source Creation | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-create-source-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-create-source-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-create-source-mobile.png) |
| Expanded Source Details | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-source-details-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-source-details-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-source-details-mobile.png) |
| Accepted Text Submission | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-ingestion-accepted-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-ingestion-accepted-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-ingestion-accepted-mobile.png) |
| Reported Workflow / Expanded Details | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-workflow-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-workflow-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-workflow-mobile.png) |
| Provider Controls / Expanded Acquisition | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-providers-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-providers-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-providers-mobile.png) |
| Security and Audit | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-security-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-security-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-security-mobile.png) |
| Expanded Audit References | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-audit-details-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-audit-details-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-audit-details-mobile.png) |
| Operations Navigation | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-navigation-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-navigation-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-navigation-mobile.png) |
| Loading Registry | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-loading-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-loading-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-loading-mobile.png) |
| Empty Registry | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-empty-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-empty-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-empty-mobile.png) |
| Forbidden Registry | [Desktop](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-error-desktop.png) | [Tablet](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-error-tablet.png) | [Mobile](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1d-error-mobile.png) |

Visual fixes included restrained desktop lookup width/alignment, stacked tablet
technical metadata, singular loaded-page counts and complete action-form framing.
Existing overview Evidence Table remains an accessible, labelled, keyboard-focusable
horizontal scroll region on smaller screens; source/provider/audit tables use
mobile records. Long URLs can wrap mid-token but do not clip.

## Review Findings and Rulings

One fresh read-only review of the complete Phase 1D implementation found no
Critical findings and two Important findings. Both are fixed and regression-tested:

1. Lost non-idempotent write responses previously claimed confirmed failure.
   Contextual feedback now reports uncertainty and appropriate inspection guidance.
2. Failed repeat batches previously cleared earlier accepted workflow references.
   References now survive pending/error repeats with previous-response labelling.

The same fix pass corrected the visible provider lookup alignment. No second
review was dispatched; final test/build and screenshot evidence validate the fixes.

Other review limits were resolved as follows:

- Legacy all-source document composition: retained deliberately; only registry
  browsing is newly bounded, avoiding a wholesale attribution rewrite.
- Backend idempotency, restart, acquisition execution and authorization behavior:
  inspected to establish frontend semantics, preserved unchanged.
- Missing workflow timestamps, source health/history/editing, provider quota and
  run discovery: honest omissions, no fabricated values or new capability.
- Provider configuration/completion wording: supported by actual backend fields,
  separate from health and ingestion success.
- Duplicate guard, cancellation, bounded paging: no additional actionable defect;
  targeted regressions pass.
- Page-local filters, First/Next navigation and source selection across pages:
  explicit supported contracts, no inferred global totals or reverse cursor.
- Malformed responses contradicting generated required fields: no evidence of
  current backend production; no speculative contract rewrite.
- Earlier phases' shared style/capitalization: retained, no material regression
  found in the production suite.
- Exhaustive accessibility and visual certification: not claimed. The review
  sampled code/screens; author inspection and browser checks cover the stated
  widths, interaction and font behavior, not a screen-reader audit.
- Reviewer did not independently execute tests: final author-run gate results
  above are the verification evidence.

## Known Gaps and Phase 1E Entry Point

No source editing, health/ownership, global ingestion history, workflow timestamps,
provider quota remaining or provider-run discovery exists in these contracts.
Provider acquisition is non-idempotent; a lost response cannot be safely treated
as no work. Manual source selection is bounded-page plus session-created/selected
records, not a fabricated global search. Audit filters are page-local and totals
are not global. Plain-text forms retain the existing English submission default.

Live backend integration and native browser zoom remain unvalidated here;
screen-reader testing and additional browser engines are also outstanding.
Temporary runtime/assets/reports stay ignored; screenshot paths are local to this
host. The final clean worktree is reported separately after the commit.

Recommend Phase 1E begin with a separately approved cross-experience accessibility
and contract-integration pass: native zoom/screen-reader/browser coverage,
read-only checks against an authorized local dataset, and identification of
needed source/run discovery or attested timing contracts. Any new backend API,
production identity flow, media service or deployment needs its own approved
scope. Phase 1E has not started.

## Complete Changed-File Manifest

27 tracked files relative to the Phase 1C base; no dependency, font, generated
schema, backend or deployment changes. Screenshots, caches and temporary reports
are excluded from Git.

```text
apps/web/README.md
apps/web/e2e/live.spec.ts
apps/web/e2e/operations-support.ts
apps/web/e2e/operations-visual.spec.ts
apps/web/e2e/operations.spec.ts
apps/web/src/app/security/page.tsx
apps/web/src/app/sources/page.tsx
apps/web/src/components/operations/operation-feedback.tsx
apps/web/src/components/operations/operations-nav.tsx
apps/web/src/components/operations/operations.module.css
apps/web/src/components/operations/source-administration.tsx
apps/web/src/components/operations/use-operation.ts
apps/web/src/components/operations/workflow-status.tsx
apps/web/src/components/pages/dashboard.tsx
apps/web/src/components/pages/security.tsx
apps/web/src/components/pages/sources.tsx
apps/web/src/components/provider-admin.tsx
apps/web/src/lib/api.ts
apps/web/src/lib/models.ts
apps/web/src/lib/operation-feedback.test.tsx
apps/web/src/lib/operations-presentation.test.tsx
apps/web/src/lib/operations.test.ts
apps/web/src/lib/operations.ts
apps/web/src/lib/pagination.test.ts
apps/web/src/lib/queries.ts
docs/frontend-design-guidance.md
docs/frontend-phase1d.md
```

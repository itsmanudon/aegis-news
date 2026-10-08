# Phase 1C — Entity Intelligence, Events and Verification

Implemented on `feat/aegis-editorial-foundation`, beginning from the clean,
expected Phase 1B HEAD `898312e247576d301d3faa1c196601520bf72951`.
Local main, origin/main and the inspected remote main remain
`49a55e583b93d506d654fe5baf102fed15cc9dc0`; the feature has no remote head.
No main changes, merge, push, deployment, release-tag operations or history
rewrite occurred. Root/frontend AGENTS and installed Next.js 16 guidance were
read before implementation. The existing checkout and all approved work remain.

Separate implementation commits:

- `5111f26ef1774e364e26e9f1fb480db88abae148`: bounded entity/event adapter pages.
- `0a78367f465fa221d362a2d2fde3b2a92339f1f0`: editorial research, timeline,
  verification workspace, model-field refinements and regression coverage.
- The final documentation commit is reported in the delivery message and
  discoverable with `git log --oneline 898312e..HEAD`.

## Delivered Design

Entity Directory presents canonical serif names, recorded entity type, aligned
creation metadata and clear navigation in unenclosed editorial rows. Entity IDs
and schema versions are in Technical Identity disclosures. Counts describe the
loaded page. No biography, alias, relationship graph, description or linked-record
total is inferred. Loading, failure and empty pages are explicit.

Entity Detail has a research heading, canonical type/creation metadata, optional
technical identity and an independent Linked Evidence stream. The existing
associated-document cursor contract supplies First Page/Next Page browsing;
evidence is no longer silently limited to the first page. Source attribution,
Publication/First Seen and availability remain visible. Phase 1B editorial rows
provide literal previews, separate full-story links and native expandable loaded
evidence. Expansion does not request intelligence for each linked document.

Events use a restrained timeline with serif summaries, recorded source/model
category, revision, Occurred and Intelligence Available groups. Unknown occurrence
times remain Unknown. Revision keys include event ID and revision. Supporting
document navigation is distinct from technical references; multiple destinations
have ordinal labels and accessible actual reference IDs. Event References contains
the supplied event/schema/revision/creation/analysis/entity/document fields.
There are no fabricated topic categories, clusters, importance or geography.

Timeline sorting and category filtering operate on the loaded page, visibly
disclosed. Timestamp sorting compares instants, places unknowns last and retains
every supplied revision. The API pages by identity/revision rather than global
chronology. Operations' small event sample now has revision-safe keys, a truthful
loaded-page note and a Browse Events link; missing supporting documents never
produce an undefined route.

Verification retains `/provenance` and becomes Select Document → Inspect Evidence
→ Run Authorized Verification → Review Outcomes. A paginated native selector
loads full evidence only for the chosen document. The single inspector presents
operation history, hash, subject/input references and the existing explicit
mutation. No check runs automatically. Selecting another document, changing the
selector page, or changing identity/mode clears mutation state and cancels old
requests. Desktop uses selector/inspector columns; mobile stacks them in DOM order.

Not Checked, Checking, Passed, Failed and Unavailable are distinct. Simulated Mock
Result is explicit. An indeterminate `unverified` fixture is Unavailable, never
Failed. Existing real content/chain/signature booleans remain separate; missing
real subchecks are unavailable rather than inferred unsigned. Mock legacy
signature values are labelled simulated; missing mock content/chain results are
not manufactured. Browser receipt time remains Response Received At, with no
server-attested timestamp claim. Cryptographic integrity does not establish
factual accuracy. `security:verify` remains enforced by the existing server.

Source Serif 4, Inter, Paper/Ink/Teal, warm controls, tabular numbers, restrained
rules and 12px disclosure surfaces are retained. Source headlines, model content
and raw technical identifiers preserve their original capitalization; authored
labels follow Title Case. No new component framework, font, asset or animation
was introduced. Discover and the Story Detail reading composition are unchanged.
The two Phase 1B model gaps are resolved: actual predicted entity type and
model-reported extraction occurrence now display, preserving Unknown/null values.
Compact model strips now use the existing 12px panel token.

## Adapter and Component Changes

Generated OpenAPI/domain types, backend payloads, routes, database/ML/ingestion
and cryptographic code are unchanged. Frontend `BoundedList<T>`, `EntityList`
and `EventList` extend the existing paged-array composition. Entity/event
methods accept an optional cursor after the existing AbortSignal argument and
return one limit-20 page with the supplied opaque `nextCursor`, replacing eager
all-page loops. Query keys include mode and cursor. Mock pages use existing
fixtures with validated offsets. No mock data becomes a Real API fallback.

Associated evidence continues using `documents({ entityId, cursor })`, limit 20,
the existing generated document endpoint and source composition. Source-registry
pagination is unchanged. There is no per-row intelligence fan-out. Full selected
verification evidence uses the existing document/intelligence query; it does not
load optional acquisition/media to run verification.

The shared provider/identity boundary, in-memory tokens, query-cache isolation,
typed errors/request IDs, request cancellation and 10-second transport deadline
are preserved. `ProvenanceCard`/`VerificationDetails` have optional workspace
presentation; Story Detail keeps its existing provenance composition. The small
CursorPager is shared only by the four paged flows actually implemented.

```text
Existing Providers / Identity Boundary / Shell / Masthead
├─ Entities → Canonical Directory Rows / Technical Identity / CursorPager
├─ EntityDetail → Canonical Header / Technical Identity
│  └─ Keyed LinkedEvidence → EditorialResults / EvidenceDisclosure / CursorPager
├─ Events → Loaded-Page Filters / Revision Timeline / Event References / CursorPager
└─ Provenance → Paginated Document Selector / Workflow
   └─ Keyed SelectedEvidence → useDocument / StoryMetadata
      └─ ProvenanceCard → useVerification / Operations / VerificationDetails
```

## Validation and Review

| Check | Exact Final Result |
| --- | --- |
| `pnpm web:api:check` | Passed, exit 0; no generated contract drift |
| `pnpm web:test` | 33 passed in 6 files, 0 failures |
| `pnpm web:typecheck` | Passed, exit 0 |
| `pnpm web:lint` | Passed, exit 0 |
| `pnpm web:build` | Passed, exit 0; all existing routes retained |
| `AEGIS_E2E_EXTERNAL_SERVER=1 pnpm web:test:e2e` | 53 passed, 6 skipped, 0 failures; 59 total, exit 0 |

Baseline was 27 unit tests and no API drift. New coverage checks bounded opaque
cursors, bearer authorization/cancellation, associated evidence paging, empty
records, native Enter/Escape/focus behavior, actual model fields, revision identity,
occurrence/availability order, no per-row requests, selection-only reads, explicit
pending verification, mixed subchecks, 403/retry, indeterminate mock results,
multiple supporting links, canceled old selections and mock/real isolation.
Existing route/security/operations/discovery/font tests remain active. Opt-in live
selectors were updated without weakening their functional assertions or running
their write-enabled flows. No snapshot baseline was silently changed.

The five live-backend skips are live MVP, historical corpus, real providers, real
volume and public-safe evidence capture. Their services/data/tokens were not
launched. The sixth skip is a native-browser-zoom probe: five Ctrl+= shortcuts
left headless Chromium's DPR and inner width unchanged, so native 200% zoom is
explicitly unverified. Five normal widths (1440/1024/768/390/320) and actual
doubled computed text sizes at a 720px viewport are checked independently.
This text-size test does not rely on CSS magnification. Browser AX inspection
samples the native disclosure semantics; manual assistive-technology testing is
not claimed. Long identifiers/names and malformed or missing times reflow.

One fresh reviewer inspected the complete Phase 1C range and pending tree.
Its indeterminate mock mapping finding and multiple-link accessibility finding
entered one fix pass. Both first reproduced failures against the production
build, then passed in the complete 53-test suite. The link finding was regraded
Important because indistinguishable destinations impede research navigation.
No unresolved review finding or deferred minor remains. Intermediate failures
were addressed; no baseline application failure was found. Non-failing browser
color warnings/Git line-ending notices remain environment output; a restricted
formatter invocation was retried successfully with the available runtime.

## Screenshots

Ten final PNGs were captured and inspected from the production standalone build
on `127.0.0.1:3104`, with loaded local fonts and mock environment default. Mock
identity/data remains visibly disclosed. Expanded evidence and simulated outcomes
are real rendered UI states. Production captures avoid the development indicator;
UI elements were not hidden or edited out. The visual gate compares typography,
spacing, mobile reflow, alignment and disclosures with Phase 1A.1/Phase 1B.

Files are outside Git at:
`C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/`

| State | File | Width |
| --- | --- | --- |
| Desktop Entity Directory | [phase1c-directory-desktop.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-directory-desktop.png) | 1440 |
| Mobile Entity Directory | [phase1c-directory-mobile.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-directory-mobile.png) | 390 |
| Desktop Entity Detail | [phase1c-entity-desktop.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-entity-desktop.png) | 1440 |
| Expanded Entity Evidence | [phase1c-entity-evidence-expanded.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-entity-evidence-expanded.png) | 1440 |
| Expanded Mobile Entity Evidence | [phase1c-entity-evidence-mobile.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-entity-evidence-mobile.png) | 390 |
| Desktop Events Timeline | [phase1c-events-desktop.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-events-desktop.png) | 1440 |
| Mobile Events Timeline | [phase1c-events-mobile.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-events-mobile.png) | 390 |
| Desktop Verification Workspace | [phase1c-verification-desktop.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-verification-desktop.png) | 1440 |
| Expanded Verification Details / Mock Outcomes | [phase1c-verification-expanded.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-verification-expanded.png) | 1440 |
| Mobile Verification Workspace | [phase1c-verification-mobile.png](C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a/phase1c-verification-mobile.png) | 390 |

Reproduce with `AEGIS_SCREENSHOT_DIR` set to an existing directory and
`pnpm --filter @aegisnews/web exec playwright test e2e/intelligence-visual.spec.ts`.
Without the variable, captures use ignored Playwright output. The default full
suite also executes the Phase 1B visual gate.

## Decisions, Limits and Phase 1D

Decisions made under the approved scope:

1. Keep the requested existing checkout/feature branch and execute inline.
   Owner visual review remains the integration gate; no repeated approval or
   separate speculative design phase was added.
2. Reuse loaded evidence expansion. Missing list intelligence is unavailable and
   full Story Detail remains the entry point; cost: no inline analysis that the
   list endpoint does not supply.
3. Use bounded local cursor state for the new flows. Mode/identity/selection
   remounts reset it; cost: these new cursor positions are not shareable/restored
   after route reload. Documents/Search retain their Phase 1B URL state.
4. Treat evidence_kind as the supported event category. No topic/event taxonomy
   field exists in NewsEvent; adding one or fetching every analysis is deferred.
5. Keep existing source-registry pagination, which may add read latency for large
   registries. Document/entity/event pages remain bounded; no backend refactor.
6. Report native zoom/live/assistive-technology limits honestly. The keyboard
   probe was attempted; production screenshots and doubled-text checks passed,
   while manual native zoom and screen-reader review remain owner-side checks.

API limits remain: no global association totals, backward cursors, guaranteed
newest-first event order, full-article completeness or server-attested check
timestamps. No biography/relationship/trend/summary capability is claimed.
Selected verification results are session state, cleared on selection/page/mode/
identity changes; they do not silently rewrite feed integrity badges or persist
as durable attestations. Production authentication remains external and unchanged.

Recommended Phase 1D: apply the same restrained UI and accessibility standards to
Sources/Admin and Operations/Security workflows, with bounded audit browsing
where supported by the existing contract. Keep authorization, write confirmations
and real/mock isolation explicit. New backend capabilities, public auth, aggregate
intelligence, media delivery and deployment require separate approval. Phase 1D
has not started; return Phase 1C for owner visual review.

## Complete Phase 1C Changed-File Manifest

All paths are relative to the repository root, covering boundary, implementation,
tests and handoff from `898312e`. No backend, generated schema, dependency, font,
license or release-tag file changed.

```text
apps/web/README.md
apps/web/e2e/console.spec.ts
apps/web/e2e/evidence.spec.ts
apps/web/e2e/historical-corpus.spec.ts
apps/web/e2e/intelligence-visual.spec.ts
apps/web/e2e/intelligence.spec.ts
apps/web/e2e/live.spec.ts
apps/web/e2e/volume.spec.ts
apps/web/src/app/entities/[id]/page.tsx
apps/web/src/app/entities/page.tsx
apps/web/src/app/provenance/page.tsx
apps/web/src/components/documents/analysis-panel.module.css
apps/web/src/components/documents/analysis-panel.tsx
apps/web/src/components/documents/provenance-card.tsx
apps/web/src/components/documents/verification-details.tsx
apps/web/src/components/pages/dashboard.tsx
apps/web/src/components/pages/entities.tsx
apps/web/src/components/pages/events.tsx
apps/web/src/components/pages/intelligence.module.css
apps/web/src/components/pages/provenance.tsx
apps/web/src/components/pages/verification.module.css
apps/web/src/components/ui/cursor-pager.module.css
apps/web/src/components/ui/cursor-pager.tsx
apps/web/src/lib/api.ts
apps/web/src/lib/models.ts
apps/web/src/lib/pagination.test.ts
apps/web/src/lib/queries.ts
apps/web/src/lib/source-presentation.test.tsx
apps/web/src/lib/source-presentation.ts
docs/frontend-design-guidance.md
docs/frontend-phase1c.md
```

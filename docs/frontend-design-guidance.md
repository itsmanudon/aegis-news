# Frontend Design Guidance

The interface reads like a publication, explores like an intelligence platform,
and verifies like a security system. Preserve source facts, model assessments and
cryptographic evidence as distinct concepts.

## Typography and Capitalization

Use Title Case for interface headings, navigation, buttons and short labels. Do
not force uppercase through CSS. Preserve acronyms (API, UTC, ID), Aegis News,
proper nouns, source headlines/body text, model-provided labels and technical
identifiers. Use sentence capitalization for explanatory body copy. Avoid applying
automatic case transformations to arbitrary API strings.

Source Serif 4 carries editorial headlines and reading text. Inter carries
controls, metadata and quantities. Use `tabular-nums lining-nums` for numeric UI.
System monospace is reserved for hashes, code and machine identifiers.

## Surfaces and Corners

Keep Paper `#F7F6F2`, Ink `#17212F`, Teal `#0F766E`, Dividers `#D6D9D6`,
Caution `#B45353`, Supporting Text `#57616D` and Surface `#FFFFFF`.
Use Filter Region `#F1F0EB` for filters and quiet table headers.

Reuse the global tokens: `--radius-small: 6px`, `--radius-control: 10px`,
`--radius-panel: 12px`, `--radius-overlay: 16px`, `--radius-pill: 999px`.
Controls use the control radius; operational containers use the panel radius;
status badges use the pill radius. Overlay is reserved for future actual overlays.
Keep editorial story rows unenclosed and separated by restrained rules/whitespace.

## Time and Controls

Reuse `Timestamp` for dates and clocks. It normalizes to UTC, preserves an exact
ISO instant in semantic `time` attributes, and displays seconds/fractions when
nonzero. Missing or malformed times remain Unknown. Publication and First Seen
are separate labelled groups; acquisition is not publication.

Navigation labels are never underlined. A current page has one 2px teal bottom
border and stronger weight. Hover changes color; keyboard focus has a separate
teal outline. Retain native select controls with clear labels and indicators.

Documents/Search retain their existing filter values and query behavior. Mobile
shows the primary text control, reset action and an accessible Advanced Filters
disclosure. Closing the disclosure preserves values; its count reflects active
advanced controls. Desktop exposes all fields. Real-mode integrity filtering
continues to report unsupported capability rather than inventing results.

## Editorial Reading and Evidence

Story Detail leads with source attribution, Publication and First Seen, extent
and an actual publisher article link when available. A source registry address
is labelled separately. Captured text is never declared the complete article
without supported evidence. Literal excerpts are source text, never generated
summaries. Source reporting precedes model assessments in DOM order; on mobile,
the detailed evidence rail follows the reading content.

Use unenclosed editorial result rows by default. Keep the dense Evidence Table
available explicitly on desktop; mobile uses rows even when the URL retains the
table preference. Expandable inner evidence surfaces use the 12px panel radius,
white backgrounds and restrained dividers. Native details/summary or semantic
buttons with associated regions provide chevrons, keyboard activation, visible
focus and Escape-to-close with focus restoration. Expansion alone does not fetch
per-row intelligence. Do not add decorative animation; any later transitions
must respect reduced-motion preferences.

Keep model output and confidence clearly attributed. Preserve actual model name,
version, availability, zero-valued confidence and supporting extraction evidence.
Hide raw IDs and hashes inside Technical Metadata rather than turning them into
an editorial headline. Preserve API-provided labels verbatim; map only explicitly
known interface enum values to Title Case.

Verification is an explicit action. Content Integrity, Chain Validity and Digital
Signature have separate outcomes. Real records remain unchecked until the check
returns. Mock badges are simulated. Browser time is Response Received At; never
imply a server-attested check time or factual truth. Acquisition/media queries
may fail independently while source reporting remains usable. Remote image and
video references retain their validation/attribution and do not become stored,
cryptographically authenticated assets.

URL filter state preserves supported literal-search values and opaque cursors.
Changes to filters clear pagination. Counts describe the loaded page; no global
recency, importance, corpus total or backward cursor is inferred.
Changing Data Mode also clears pagination: an opaque cursor belongs to the
adapter that issued it, while filter values remain shareable.

## Entity Research, Events and Verification

Entity Directory emphasizes canonical name and recorded type. Keep creation
metadata aligned and put technical IDs/schema versions in native disclosures.
Do not infer biographies, aliases, relationships or global linked-record counts.
Entity Detail presents paginated associated source evidence using the editorial
rows. Expansion reveals loaded evidence; extra intelligence stays on Story
Detail rather than being requested per row.

Events display source statements and model outputs with separate Occurred and
Intelligence Available metadata. Unknown occurrence times remain Unknown. Key
every revision by event ID plus revision. Only sort/filter the loaded page when
the cursor API orders records by identity/revision. Show revision-safe supporting
links and available analysis references without generating an event taxonomy.
Distinguish multiple document destinations with ordinal labels and actual
reference identification; do not fetch titles for every event link.

Verification uses one selected document and one evidence inspector. The selector
precedes the inspector in DOM order and stacks above it on mobile. No check runs
until the explicit action. Distinguish Not Checked, Checking, Passed, Failed,
Unavailable and Simulated Mock Result. An unverified/indeterminate mock result
is Unavailable, never an invented failure. Missing real subchecks remain
unreported; do not infer unsigned evidence from an error or missing records.
Preserve the supported Content Integrity, Provenance Chain and Digital Signature
outcomes, operations/hashes/input/subject references and browser receipt label.
Selection, selector pagination, identity and mode changes clear mutation state
and cancel old requests. No new cryptography or server authorization is added.

Use 12px compact model-output strips consistently with other inner evidence
surfaces. Preserve actual entity-extraction predicted type and event-extraction
occurrence values, including Unknown when absent. These remain model reports,
not established classifications or facts.

## Operations and Security

Use Inter for dense operational records, forms, counts and statuses; reserve
serif typography for the page heading. Browse records before action forms.
Keep tables aligned on desktop and reflow into labelled records on mobile.
Technical IDs, hashes and raw responses belong in 12px native disclosures;
long references wrap without horizontal clipping. Preserve actual API strings.
Source and audit counts describe a single bounded page. Audit filters apply to
that page; success/failure must not be relabelled allowed/denied.

Separate source creation, captured text submission, known workflow lookup and
provider acquisition. Scope requirements are visible; the server remains the
authorization authority. Controls disable during writes, synchronous duplicate
guards prevent accidental resubmission, and identity/mode changes cancel work.
No acquisition, mutation retry or status polling runs automatically.

Acceptance is separate from workflow state. Provider configuration is separate
from health, and acquisition completion is separate from ingestion completion.
Unknown states stay unknown. Lost write responses can leave accepted work:
show Request Outcome Unknown rather than confirmed failure, and explain the
appropriate inspection or unchanged-key retry behavior. Keep earlier accepted
workflow references after subsequent failures, explicitly labelled Previous
Accepted Response. Do not invent pipeline history, timestamps or quotas.

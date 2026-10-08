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

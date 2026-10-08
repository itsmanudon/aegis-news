<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## UI Typography and Capitalization Rule

- Use Title Case for user-facing headings, section headings, navigation labels,
  buttons, short control labels, and interface section names.
- Never force all-uppercase presentation through CSS `text-transform: uppercase`.
- Preserve established acronyms, brand capitalization, proper nouns, code
  identifiers, and source-provided content.
- Long-form body copy should use normal sentence capitalization for readability.
- Prefer restrained typography with clear visual hierarchy rather than uppercase
  micro-labels with exaggerated letter spacing.
- Apply this project design rule consistently across News & Intelligence and
  Operations & Security. Shared tokens and presentation guidance are documented in
  [Frontend Design Guidance](../../docs/frontend-design-guidance.md).

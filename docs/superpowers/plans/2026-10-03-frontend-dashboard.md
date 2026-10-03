# Analyst console implementation plan

Goal: Build the authorized Agent 4 dashboard on base 0203ae95, without changing backend contracts.

Architecture: App Router pages share a navigation shell and TanStack Query provider. A frontend adapter supplies generated domain records plus explicitly frontend-only presentation metadata. Mock and real modes have isolated query caches; real mode uses only paths in the checked-in OpenAPI schema and reports missing capabilities.

Design: Slate #182b40 navigation, paper #f3f6fa workspace, white #ffffff panels, blue #235fba links, green #236446 verified state, amber #865500 caution. Segoe UI headings/body and Consolas data labels. Dense document tables and a four-stage availability rail convey the intelligence workflow. No hero graphics, market charts, or decorative motion.

Implementation and checks:
- [x] Generate OpenAPI and domain TypeScript with a reproducible drift check.
- [x] Write adapter tests for filtering, missing documents, unavailable real capabilities, and knowledge cutoffs; verify failures before implementation.
- [x] Build typed fixtures, centralized client, mode/identity provider, shared accessible UI primitives.
- [x] Implement dashboard, documents/detail, entities/detail, timeline, search, provenance, security, and source shell.
- [x] Verify mocked navigation, filtering, evidence distinction, verification, responsive navigation, and real-mode isolation with Playwright.
- [x] Run final tests, generation check, TypeScript, lint, and production build. Review final diff and commit on feat/frontend-dashboard.

Integration boundaries: No future endpoint URLs, signature formats, auth scopes, or security guarantees are invented. Missing domain associations are presentation composition only. Identity is a frontend session port; real mode is anonymous until OIDC is integrated. UI permissions never claim server enforcement.

Verification: 12 unit/component tests passed, 10 Chromium browser flows passed, generated-type check passed, TypeScript and ESLint passed, production build passed. The existing Python suite passed 114 tests and skipped 11 service-dependent tests. Independent review found no remaining important issues after deadline, UTC normalization and existing smoke-test fixes. Windows browser tests used a preinstalled Chromium and an explicitly managed local mock server to avoid process teardown delays.

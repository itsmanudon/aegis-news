# Phase 6 validation ledger

Release reference: [v0.1.0-mvp record](../mvp-release.md). Phase 6 runs only on
`phase6/evaluation-demo-hardening`; no automatic merge or second release tag.

## Executed local checks

| Check | Result |
|---|---|
| Ruff formatting/lint | Passed |
| Strict mypy | Passed, 97 source files |
| Backend full live suite | 241 passed, no skips, one existing Starlette/httpx deprecation warning |
| Category breakdown | 83 unit, 91 contract, 34 security, 16 ingestion, 16 integration, 1 HTTP E2E |
| Real infrastructure | PostgreSQL, Redis, MinIO and Temporal exercised |
| New reliability seam | Post-commit failure, worker restart, stable analyses/outbox and valid provenance passed |
| Migrations | Fresh upgrade, safe scratch downgrade/re-upgrade paths and metadata checks passed |
| Frontend unit/components | 12 passed |
| Frontend lint/typecheck/production build | Passed |
| OpenAPI/domain/TypeScript drift | Passed |
| Real browser flow | Passed |
| Evidence capture | Passed after fixing Grafana login race; ten JPEG screenshots |
| Demo reset/seed | Fresh local project volumes and keys regenerated; known logical dataset restored |
| Security demo | 14 checks passed, including timed tamper window and restoration |
| Original acceptance | 22/22 controls passed |
| Pipeline benchmark | Fresh five-item batch; actual Temporal activity timing; repeated keys reuse results |
| Observability | Prometheus up, provisioned Grafana, correlated Loki logs, matching OTel worker trace receipt |
| Production dependency audits | Python and pnpm: no known vulnerabilities |
| Repository secret guard | Passed |

Mock Playwright, final visual recapture, gitleaks and hosted Phase 6 CI outcomes are
recorded below when completed. No in-progress job is represented as success.

## Full backend command (PowerShell)

```powershell
New-Item -ItemType Directory -Force .test-tmp, .integration-results | Out-Null
$env:AEGIS_AI_PROFILE = 'offline'
$env:AEGIS_RUN_INTEGRATION = '1'
$env:AEGIS_RUN_E2E = '1'
$env:AEGIS_DATABASE_URL = 'postgresql+psycopg://aegis:aegis_dev_only@127.0.0.1:35432/aegisnews?connect_timeout=5'
$env:AEGIS_INGESTION_TEST_DATABASE_URL = $env:AEGIS_DATABASE_URL
$env:AEGIS_REDIS_URL = 'redis://127.0.0.1:36379/0'
$env:AEGIS_S3_ENDPOINT_URL = 'http://127.0.0.1:39000'
$env:AEGIS_TEMPORAL_ADDRESS = '127.0.0.1:37233'
$env:AEGIS_TEMPORAL_TEST_ADDRESS = $env:AEGIS_TEMPORAL_ADDRESS
$env:AEGIS_INGESTION_TEST_TEMPORAL = '1'
$env:AEGIS_INGESTION_TEST_MINIO = 'http://127.0.0.1:39000'
$env:AEGIS_TEST_API_URL = 'http://127.0.0.1:38000'
$env:AEGIS_TEST_WEB_URL = 'http://127.0.0.1:33000'
uv run pytest -q -rs --basetemp=.test-tmp/full-run --junitxml=.integration-results/backend.xml
uv run python scripts/verify_migrations.py
```

Use a new basetemp name for another Windows run if previous temporary ACLs interfere.
On POSIX export the same environment variables and run the same uv commands. A normal
`uv run pytest -q` skips infrastructure checks unless explicitly enabled, by design.

Other reproducible commands:

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run python scripts/export_schemas.py --check
uv run python scripts/scan_secrets.py
pnpm web:lint
pnpm web:typecheck
pnpm web:test
pnpm web:api:check
pnpm web:build
pnpm web:test:e2e
```

Use `pnpm.cmd` on Windows. Clear live/external flags for the mock browser suite; live
commands and Docker/security/reset reproduction are in demo-guide.md. Dependency audit
uses a frozen `uv export --no-dev --no-emit-project` requirements file with pip-audit,
plus `pnpm audit --prod`. Git history is checked with the existing gitleaks CI configuration.

## Failures investigated and limitations

Phase A's single-quoted Redis health command failed on the Actions process parser and
was fixed without product changes; branch and released main CI then passed. Phase 6
setup initially lacked local pytest/output parent directories; those were initialized.
Grafana screenshot navigation raced login completion and now awaits it. Immediate
collector-tail checking failed under asynchronous export; the final tool polls bounded
logs and requires an exact trace ID match. These failed attempts are not counted as passes.

Light/full models are not installed: local-only probes reported ModelUnavailable. No
pretrained quality, model download-size or GPU/RAM benchmark is claimed. Human gold
adjudication and production security/availability are outside this evidence. Public data
and original image are CC0; the repository currently lacks a project-code LICENSE file,
whose choice remains an owner decision. No machine-specific paths or private keys belong
in committed documents/reports. Existing Starlette deprecation and Node color warnings
remain non-failing. The full local benchmark is n=5 and not a scaling experiment.

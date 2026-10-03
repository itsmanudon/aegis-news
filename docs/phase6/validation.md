# Phase 6 validation ledger

This is the historical Phase 6 ledger. Later evaluation-only work is recorded in the
[gold v2 validation ledger](../evaluation/validation.md); original counts/results below
are not claims about that later branch.

Release reference: [v0.1.0-mvp record](../mvp-release.md). Phase 6 runs only on
`phase6/evaluation-demo-hardening`; no automatic merge or second release tag.

## Executed local checks

| Check | Result |
|---|---|
| Ruff formatting/lint | Passed |
| Strict mypy | Passed, 97 source files |
| Backend full live suite | 246 passed, no skips, one existing Starlette/httpx deprecation warning |
| Category breakdown | 88 unit, 91 contract, 34 security, 16 ingestion, 16 integration, 1 HTTP E2E |
| Real infrastructure | PostgreSQL, Redis, MinIO and Temporal exercised |
| New reliability seam | Post-commit failure, worker restart, stable analyses/outbox and valid provenance passed |
| Migrations | Fresh upgrade, safe scratch downgrade/re-upgrade paths and metadata checks passed |
| Frontend unit/components | 12 passed |
| Frontend lint/typecheck/production build | Passed |
| OpenAPI/domain/TypeScript drift | Passed |
| Mock browser flows | 10 passed; two live-only flows intentionally skipped in this mode |
| Real browser flow and evidence capture | 2 passed; ten JPEG screenshots, 1.06 MB combined |
| Demo reset/seed | Fresh local project volumes and keys regenerated; known logical dataset restored |
| Security demo | 14 checks passed, including timed tamper window and restoration |
| Original acceptance | 22/22 controls passed |
| Pipeline benchmark | Fresh five-item batch; actual Temporal activity timing; repeated keys reuse results |
| Observability | Prometheus up, provisioned Grafana, correlated Loki logs, matching OTel worker trace receipt |
| Production dependency audits | Python and pnpm: no known vulnerabilities |
| Repository secret guard | Passed |
| Gitleaks branch history | Five implementation/fix commits scanned, no leaks; hosted security also passed |
| Independent review fixes | Five regressions observed RED then GREEN; full live suite 246/246 |
| Assessment reproducibility | All metrics and nearest neighbors equal across two independent offline runs |

Hosted [run 37110008028](https://github.com/itsmanudon/aegis-news/actions/runs/37110008028)
passed backend, frontend, migrations, security and optional local-mvp jobs on `03064ee`.
The latter built fresh Linux Docker services, ran 22/22 original acceptance checks,
demo seed/benchmark/14 security checks and the live browser flow. The earlier push
run 37109987974 was canceled by same-ref concurrency when manual dispatch started.
Final review fixes at `b28d0b1562c3a455874c1521542d10eab7c437bb` passed all five jobs in
[run 37110699103](https://github.com/itsmanudon/aegis-news/actions/runs/37110699103),
including fresh Linux full-stack startup, acceptance, seed, benchmark, security and
live browser checks. Push run 37110698757 was superseded by that manual run through
the configured concurrency group. There were no Phase 6 hosted test failures.

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
Mock Playwright assertions passed but its local dev-server teardown hung under process
sandboxing; the verified mock-only process tree was stopped and the normal-permission
rerun exited successfully. Review found inherited Compose reset configuration, random
assessment tie ordering and incorrect inference-failure status; all were corrected and
covered by regression tests. Fresh reset with an unrelated `COMPOSE_FILE` succeeded
using only the pinned demo configuration, followed by security/acceptance/telemetry checks.
Final interruption/resume passed with valid provenance. A fresh post-restart batch
completed with median 56.103 s including initial workflow-task scheduling delay; cached
replay then correctly reported zero fresh documents and null fresh throughput. Both
fast and slow measurements are documented; no production latency bound is claimed.

Light/full models are not installed: local-only probes reported ModelUnavailable. No
pretrained quality, model download-size or GPU/RAM benchmark is claimed. Human gold
adjudication and production security/availability are outside this evidence. Public data
and original image are CC0; the repository currently lacks a project-code LICENSE file,
whose choice remains an owner decision. No machine-specific paths or private keys belong
in committed documents/reports. Existing Starlette deprecation and Node color warnings
remain non-failing. The full local benchmark is n=5 and not a scaling experiment.
Deferred review minor: percentile indexing has an off-by-one boundary when 0.95*n is
integral; published n=5/16/48 measurements are unaffected. Fix before larger benchmarks.

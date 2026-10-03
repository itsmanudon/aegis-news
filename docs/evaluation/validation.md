# Gold v2 evaluation validation ledger

Date: 2026-10-03. Base: `3c563a72a1c80fe50fe1fbdad25e69e8e7dfac0c`.
Branch: `eval/human-review-light-models`. No main merge/rebase/tag movement.
Product providers, model specs, thresholds, rules, taxonomies, contracts and normal
CI workflow are unchanged. Only evaluation tooling, a percentile correction, portable
file-byte policy, tests, evidence and documentation were added.

## Executed checks

| Check | Result |
|---|---|
| Existing optional model downloader | Three configured pinned Light snapshots downloaded explicitly; file hashes/sizes recorded; no weights in Git |
| Agent semantic review | All 16 cases reviewed before new inference; two label decisions changed; independent human sign-off pending |
| Dataset integrity | Manifest SHA-256/byte counts, exact spans/IDs and annotation counts verified; UTF-8/LF pinned across platforms |
| Offline quality | Completed, whole-profile valid, 16 cases on gold v2 |
| Real pretrained Light quality | Completed, whole-profile valid, 16 identical cases; only valid empty findings, no unavailable models |
| Dedicated performance | Separate processes; one cold document, full unmeasured warmup, 48 warm passes per profile; sampled RSS and stage/load timing recorded |
| Complete pipeline | Final Offline/Light each completed two fresh five-item batches, 30 immutable analyses per batch, linked media, valid provenance and stable duplicate retries |
| Missing-model pipeline | Empty cache plus network-disabled Light completed ten fresh documents; baseline topics/events persisted, optional stages unavailable, verification/duplicates passed |
| Ruff formatting/lint | Passed |
| Strict mypy | Passed on Windows and with Linux platform analysis, 100 source files |
| Full relevant backend suite | Final after CI fixes: 253 passed, one HTTP/browser E2E intentionally skipped, 23.52 s; earlier full runs: 251 then 252 passed as tests were added |
| Evaluation seam suite | 15 passed; exact manifests/tampering, label preservation, fair report inputs/specs, stale pollers, local-only targets, p95 and closed scanner exceptions |
| Backend contracts/security/infrastructure | Included in the full suite; PostgreSQL, Redis, MinIO, actual Temporal workflow/retry/restart exercised |
| Migrations | Scratch fresh upgrade/metadata check; downgrade to foundation/re-upgrade; downgrade to base/re-upgrade; all passed |
| OpenAPI/JSON contract drift | Passed; no schemas changed |
| Generated frontend types | `pnpm web:api:check` passed |
| Frontend typecheck/production build | Passed; frontend implementation unchanged |
| Secret guard | Passed; keys/caches/environments excluded |
| Gitleaks v8.24.2 | Full local history passed with exact public-checksum exception; two synthetic positive controls remained detected |
| Figure/table | Generated from comparable raw reports; confusion matrix visually inspected |

Normal CI remains CPU/offline with no optional inference packages, model downloads,
GPU, paid API or external credentials. The evaluation branch is pushed solely for
Linux/offline CI and review, including the portable dataset-hash regression. Hosted
results are reported with the final handoff rather than treating workflow start as success.

The final full run includes the last added report-consistency test. Category totals
are 96 unit, 91 contract, 34 security, 16 ingestion and 16 integration passes; the
single HTTP/browser E2E is skipped. Earlier run counts are preserved above.

## Failure and correction record

1. The p95 regression observed rank 20 instead of 19 for 20 values. The common helper
   now uses nearest rank `ceil(.95*n)-1`; rank-20/rank-80 boundaries and n=5 pass.
   This is a measurement defect, not tuning. Historical n=5/n=48 results are unchanged.
2. Initial pytest temp/cache directories crossed Windows sandbox/user ownership. A
   diagnostic attempt also lacked the basetemp parent. Checks were rerun under the
   environment owner with a dedicated created parent and cache provider disabled.
3. Initial pipeline readiness accepted stale pollers. A PID-based correction timed
   out because the Windows venv launcher has a child interpreter PID. A unique SDK
   benchmark identity now selects its exact live poller. Initial measured batches
   remain `*-pipeline-initial.json`; the timed-out attempt produced no official report.
4. Windows CRLF checkout bytes differed from Git/Linux bytes, invalidating portable
   raw-file hash expectations. Targeted `.gitattributes` pins evaluation files to LF;
   manifests use canonical exact bytes. Existing v1 Git content remains unchanged.
5. A localhost-based full backend run stalled on database setup; the same fixture
   completed in 0.74 s using explicit IPv4. That stalled run was stopped and rerun on
   `127.0.0.1`. The recorded pipeline measurements retain their original localhost
   protocol, not selectively replaced timings.
6. That IPv4 full run reported 249 passed, one skipped and two failures: foundation
   workflow timeout with no shared worker, and CORS preflight denied because local
   demo settings allow port 33000 while the fixture expects port 3000. Starting the
   existing offline worker and setting the test's expected CORS origin resolved both
   (two targeted tests passed), then the full suite passed. No product fix was needed.
7. New scripts had routine line-length lint findings during implementation; final
   formatting/lint checks were rerun after correcting them.
8. Hosted [run 37132473177](https://github.com/itsmanudon/aegis-news/actions/runs/37132473177)
   passed frontend/migrations but failed Linux mypy on a Windows-only subprocess
   constant and Gitleaks on 12 public tokenizer-checksum fields. The subprocess lookup
   now uses a platform-safe fallback. The inherited generic-key rule has an AND
   exception for exactly one receipt path and ten verified public checksum values;
   no whole path, arbitrary hex string, commit or secret rule is excluded. A positive
   control and regression check ensure unknown keys remain detected. CI workflows
   and inference profiles remain unchanged. No history was rewritten.

An existing Starlette/httpx TestClient deprecation warning remains. The HTTP E2E needs
a running web service and is intentionally skipped in this narrow phase; local frontend
browser flows were not requalified because no frontend behavior changed. GPU and Full
inference were not attempted. No claim is made for unexecuted validations.

## Reproduction of backend validation

Use the isolated API/dependencies plus the existing offline Docker worker:

```powershell
docker compose -f compose.yaml --env-file infrastructure/demo.env.example -p aegis-eval --profile full up -d worker
$env:AEGIS_DATABASE_URL='postgresql+psycopg://aegis:aegis_dev_only@127.0.0.1:35432/aegisnews'
$env:AEGIS_REDIS_URL='redis://127.0.0.1:36379/0'
$env:AEGIS_S3_ENDPOINT_URL='http://127.0.0.1:39000'
$env:AEGIS_TEMPORAL_ADDRESS='127.0.0.1:37233'
$env:AEGIS_CORS_ORIGINS='["http://localhost:3000"]'
$env:AEGIS_RUN_INTEGRATION='1'
$env:AEGIS_INGESTION_TEST_DATABASE_URL=$env:AEGIS_DATABASE_URL
$env:AEGIS_INGESTION_TEST_TEMPORAL='1'
$env:AEGIS_INGESTION_TEST_MINIO=$env:AEGIS_S3_ENDPOINT_URL
$env:AEGIS_TEMPORAL_TEST_ADDRESS=$env:AEGIS_TEMPORAL_ADDRESS
New-Item -ItemType Directory -Force .test-tmp | Out-Null
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=.test-tmp/evaluation-final
.venv/Scripts/python.exe scripts/verify_migrations.py
```

Use a new basetemp name or remove only its verified owned path before repeating on
Windows; pytest may create private ACLs. The migration runner owns and removes its
scratch database. Application/model caches and all release tags are preserved.

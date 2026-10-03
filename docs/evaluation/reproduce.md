# Reproduce gold v2 evaluation

Use the evaluation branch or its reviewed commit; keep release tags unchanged. This
guide evaluates the existing profiles. It does not train, tune or download Full models.
Run from the repository root. Weight/cache directories stay outside Git. `.venv-light`,
`.evaluation-tmp`, `.keys` and `.integration-results` are ignored and excluded from
Docker build context where applicable.

## Inputs and the normal environment

```sh
uv sync --frozen
uv run python -c "from pathlib import Path; from scripts.benchmark_profiles import verify_manifest; verify_manifest(Path('ml/datasets/gold/manifest-v2.json')); print('dataset hashes verified')"
uv run python -m aegis.intelligence.assessment --dataset ml/datasets/gold/assessment-v2.json --profile offline --rounds 1 --output .integration-results/review-offline.json
```

Do not rebuild/overwrite v1 or tune on v2. Review decisions are in
[ADJUDICATION-v2.md](../../ml/datasets/gold/ADJUDICATION-v2.md). Check the output's
`execution_status` and `quality_metrics_valid_for_whole_profile`; a missing-model probe
is not a successful pretrained benchmark. Genuine `NoPredictions` keeps scoring
denominators and is not an unavailable model. The partial-result assessment CLI retains
diagnostics, so its exit code alone is insufficient to claim whole-profile success.

## Optional Light environment and explicit download

Windows PowerShell:

```powershell
uv venv .venv-light --python 3.12
uv pip install --python .venv-light/Scripts/python.exe --torch-backend cpu -e . -r ml/models/requirements-local.txt -r ml/evaluation/requirements-local.txt -c ml/evaluation/light-windows-cpu-constraints.txt
.venv-light/Scripts/python.exe -c "from pathlib import Path; Path('.evaluation-tmp').mkdir(exist_ok=True)"
.venv-light/Scripts/python.exe -m aegis.intelligence.models --profile light --download --manifest .evaluation-tmp/light-download-manifest.json
```

On macOS/Linux use `.venv-light/bin/python` instead of `.venv-light/Scripts/python.exe`.
The constraints file records the actual Windows CPU packages, not a universal platform
lock: if that platform cannot install an exact wheel, omit the optional constraints and
record the actual resolved versions. `uv.lock` continues to own the normal application/
CI environment. The existing model requirements remain optional; measured package and
artifact versions are in [the receipt](../../ml/evaluation/results/gold-v2-light-artifacts.json).

Downloads use pinned revisions and required PyTorch/config/tokenizer files in the
normal Hugging Face cache. Allow about 920 MiB for selected model snapshots plus Python/
PyTorch packages. No Hugging Face token, paid API or GPU is needed for these public models.
Run the network/download step explicitly; application/container startup remains local-only.

## Comparable quality and latency

Run both profiles in the same optional environment, after the inputs are frozen:

```powershell
.venv-light/Scripts/python.exe -m aegis.intelligence.assessment --dataset ml/datasets/gold/assessment-v2.json --profile offline --rounds 1 --output .integration-results/review-offline.json
.venv-light/Scripts/python.exe -m aegis.intelligence.assessment --dataset ml/datasets/gold/assessment-v2.json --profile light --rounds 1 --output .integration-results/review-light.json
.venv-light/Scripts/python.exe -m scripts.benchmark_profiles --profile offline --rounds 3 --output .integration-results/offline-performance.json
.venv-light/Scripts/python.exe -m scripts.benchmark_profiles --profile light --rounds 3 --output .integration-results/light-performance.json
```

Compare identical `dataset_sha256` values and whole-profile validity before interpreting
quality deltas. The separate performance commands verify manifest hashes and abort on
inference/model failures. They record cold model load/import time separately from 48
warm passes after one full warmup, per-document/stage latency, nearest-rank p95, throughput
and 20-ms sampled process RSS. CPU/thread defaults are not optimized between profiles.
OS disk cache is not flushed. Quality timing includes tracemalloc and is not the published
steady-state performance measurement. GPU is optional and was not evaluated here.

Regenerate the presentation table/figure from the committed comparable evidence:

```powershell
.venv-light/Scripts/python.exe -m scripts.render_evaluation_evidence
```

## Real pipeline comparison

Use the dedicated `aegis-eval` project and free demo ports. Keep the normal Docker worker
stopped: the benchmark starts one local worker from the optional environment, waits for
its unique SDK poller identity, and terminates it after each profile. It never deletes
database/object data and creates new ingestion keys per batch.

```powershell
docker compose -f compose.yaml --env-file infrastructure/demo.env.example -p aegis-eval --profile full up --build -d --wait api temporal
.venv-light/Scripts/python.exe -c "from pathlib import Path; Path('.keys/evaluation').mkdir(parents=True, exist_ok=True)"
docker cp aegis-eval-api-1:/var/lib/aegis/keys/. .keys/evaluation

$env:AEGIS_DATABASE_URL='postgresql+psycopg://aegis:aegis_dev_only@localhost:35432/aegisnews'
$env:AEGIS_REDIS_URL='redis://localhost:36379/0'
$env:AEGIS_S3_ENDPOINT_URL='http://localhost:39000'
$env:AEGIS_S3_ACCESS_KEY='aegis_dev'
$env:AEGIS_S3_SECRET_KEY='aegis_dev_only'
$env:AEGIS_TEMPORAL_ADDRESS='localhost:37233'
$env:AEGIS_TEMPORAL_ENABLED='true'
$env:AEGIS_ENVIRONMENT='development'
$env:AEGIS_SECURITY_ENABLED='true'
$env:AEGIS_DEV_IDENTITY_ENABLED='true'
$env:AEGIS_OIDC_ISSUER='http://aegis.local'
$env:AEGIS_OIDC_AUDIENCE='aegisnews'
$env:AEGIS_OIDC_ALGORITHMS='["EdDSA"]'
$env:AEGIS_SECURITY_KEY_DIRECTORY='.keys/evaluation'
$env:AEGIS_PROVENANCE_KEY_ID='local'
$env:AEGIS_SECURITY_PERSIST_AUDIT='true'
$env:AEGIS_OTEL_ENABLED='false'

.venv-light/Scripts/python.exe -m scripts.benchmark_pipeline_profiles --profile offline --output .integration-results/offline-pipeline.json
.venv-light/Scripts/python.exe -m scripts.benchmark_pipeline_profiles --profile light --output .integration-results/light-pipeline.json
```

These are explicit public local development credentials, not production credentials.
Copying dev keys enables the local worker to sign artifacts trusted by the local API;
never commit or print key contents/tokens. On macOS/Linux set the same variables with
`export NAME=value` and use the `bin/python` interpreter. Do not target remote services;
the benchmark checks API/database/Redis/MinIO/Temporal are loopback and identity is dev-only.

The recorded comparison used `localhost`. On this Windows host a separate backend
test run experienced substantial localhost connection delays; explicit `127.0.0.1`
made the same database test complete in under a second. For troubleshooting, use IPv4
consistently in all addresses and `--api-url http://127.0.0.1:38000`, and record that
protocol change. Do not selectively replace only a slower profile's measurements.

Each profile runs one model-cold and one warm five-document batch; the first includes
model loading, not downloads/install. Workflow history records stage/total durations.
All returned documents are provenance-verified and duplicate keys must reuse workflows.
Inspect `persisted_models`: successful ingestion alone does not prove Light models ran.

To reproduce graceful missing-model behavior separately, set an **empty** ignored
`HF_HOME`, keep `HF_HUB_OFFLINE=1`, and run Light to a different output filename. Baseline
topics/events still persist; optional unavailable stages must not be called pretrained
results. Restore the normal `HF_HOME` afterward. Do not delete the normal model cache.

Stop only this evaluation project's containers; retain its volumes for inspection:

```powershell
docker compose -f compose.yaml --env-file infrastructure/demo.env.example -p aegis-eval --profile full down
```

## Validation and interpretation

[Validation ledger](validation.md) records executed checks and environment issues.
Normal CI remains offline; Light execution is an explicit local action. The checked-in
reports are immutable evidence snapshots, not freshly measured on every CI run.
Have a human reviewer sign off and obtain a separate licensed held-out corpus before
claiming general news quality. Full/GPU benchmarking and model tuning are not part of
this phase.

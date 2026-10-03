# Reproduce Gold v3 Human CPU/CUDA evaluation

Run from the repository root. Do not tune against these 16 frozen cases. Use the locked
`.venv` for validation, optional `.venv-light` for CPU, and separate ignored
`.venv-light-gpu` for CUDA. Normal CI needs no models or GPU. These commands reproduce
the measured Windows setup; other platforms need their official compatible torch build
and `bin/python`/`export` equivalents. CUDA is unavailable on macOS.

## Frozen dataset

```powershell
.venv/Scripts/python.exe -m scripts.validate_gold_v3
```

This verifies the committed manifest without rewriting it. Pending review, unlogged
changes, changed documents, invalid spans or bad hashes block execution.

## Optional CUDA setup

Inspect the driver first. The measured 610.74 driver supports the selected official
CUDA 13.0 build. Keep the normal CPU environment unchanged.

```powershell
nvidia-smi
uv venv .venv-light-gpu --python .venv-light/Scripts/python.exe
@'
from pathlib import Path
p = Path('.evaluation-tmp')
p.mkdir(exist_ok=True)
s = Path('ml/evaluation/light-windows-cpu-constraints.txt').read_text()
(p / 'gpu-constraints.txt').write_text(s.replace('torch==2.14.1+cpu', 'torch==2.14.1+cu130'))
'@ | .venv/Scripts/python.exe -
uv pip sync --python .venv-light-gpu/Scripts/python.exe .evaluation-tmp/gpu-constraints.txt --extra-index-url https://download.pytorch.org/whl/cu130 --index-strategy unsafe-best-match
.venv-light-gpu/Scripts/python.exe -c "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
```

The installer reported approximately 1.9 GiB for the CUDA wheel. This is explicit local
setup only. If model weights are absent, use the [existing pinned downloader](reproduce.md).
Evaluation never downloads or substitutes weights. Both devices use unchanged revisions.
Official sources: [PyTorch wheel index](https://download.pytorch.org/whl/cu130/torch/),
[NVIDIA driver compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).

## Quality and steady-state runtime

Run fresh processes sequentially. These outputs are ignored experiment files, preserving
committed evidence. All quality passes retain full predictions for device comparison.

```powershell
$env:HF_HUB_OFFLINE='1'
.venv-light/Scripts/python.exe -m scripts.evaluate_reviewed --profile offline --output .evaluation-tmp/gold-v3-offline.json
.venv-light/Scripts/python.exe -m scripts.evaluate_reviewed --profile light --output .evaluation-tmp/gold-v3-light-cpu.json
.venv-light-gpu/Scripts/python.exe -m scripts.evaluate_reviewed --profile light --device cuda:0 --output .evaluation-tmp/gold-v3-light-gpu.json
.venv-light/Scripts/python.exe -m scripts.benchmark_profiles --profile offline --dataset ml/datasets/gold/assessment-v3-human.json --manifest ml/datasets/gold/manifest-v3-human.json --rounds 3 --output .evaluation-tmp/gold-v3-offline-performance.json
.venv-light/Scripts/python.exe -m scripts.benchmark_profiles --profile light --dataset ml/datasets/gold/assessment-v3-human.json --manifest ml/datasets/gold/manifest-v3-human.json --rounds 3 --output .evaluation-tmp/gold-v3-light-cpu-performance.json
.venv-light-gpu/Scripts/python.exe -m scripts.benchmark_profiles --profile light --device cuda:0 --dataset ml/datasets/gold/assessment-v3-human.json --manifest ml/datasets/gold/manifest-v3-human.json --rounds 3 --output .evaluation-tmp/gold-v3-light-gpu-performance.json
```

GPU `device_setup_ms` includes import/verification before the timed cold document.
Model loader times include remaining lazy imports. Warm timings synchronize CUDA and
retain the same seven tasks, one full warmup and three rounds. Quality-report tracemalloc
timing is separate from the published runtime benchmark.

## Full workflow batches

Use a new isolated project and new ignored key directory for a clean start. Check ports
are free and preserve other projects. If the project already exists, retain its keys/
nonce counters and inspect unfinished workflows; do not recopy or reset used keys.

```powershell
$env:AEGIS_OTEL_ENABLED='false'
docker compose -f compose.yaml --env-file infrastructure/demo.env.example -p aegis-gold-v3 --profile full up --build -d --wait api temporal
# Only for a fresh project and unused directory:
if (Test-Path .keys/gold-v3) { throw 'Existing keys: retain nonce state; do not recopy.' }
New-Item -ItemType Directory -Path .keys/gold-v3 | Out-Null
docker cp aegis-gold-v3-api-1:/var/lib/aegis/keys/. .keys/gold-v3
$env:AEGIS_DATABASE_URL='postgresql+psycopg://aegis:aegis_dev_only@127.0.0.1:35432/aegisnews'
$env:AEGIS_REDIS_URL='redis://127.0.0.1:36379/0'
$env:AEGIS_S3_ENDPOINT_URL='http://127.0.0.1:39000'
$env:AEGIS_S3_ACCESS_KEY='aegis_dev'
$env:AEGIS_S3_SECRET_KEY='aegis_dev_only'
$env:AEGIS_TEMPORAL_ADDRESS='127.0.0.1:37233'
$env:AEGIS_TEMPORAL_ENABLED='true'
$env:AEGIS_ENVIRONMENT='development'
$env:AEGIS_SECURITY_ENABLED='true'
$env:AEGIS_DEV_IDENTITY_ENABLED='true'
$env:AEGIS_OIDC_ISSUER='http://aegis.local'
$env:AEGIS_OIDC_AUDIENCE='aegisnews'
$env:AEGIS_OIDC_ALGORITHMS='["EdDSA"]'
$env:AEGIS_SECURITY_KEY_DIRECTORY='.keys/gold-v3'
$env:AEGIS_PROVENANCE_KEY_ID='local'
$env:AEGIS_SECURITY_PERSIST_AUDIT='true'
$env:HF_HUB_OFFLINE='1'
.venv-light/Scripts/python.exe -m scripts.benchmark_pipeline_profiles --profile offline --api-url http://127.0.0.1:38000 --rounds 1 --output .evaluation-tmp/gold-v3-offline-pipeline.json
.venv-light/Scripts/python.exe -m scripts.benchmark_pipeline_profiles --profile light --api-url http://127.0.0.1:38000 --rounds 1 --output .evaluation-tmp/gold-v3-light-cpu-pipeline.json
.venv-light-gpu/Scripts/python.exe -m scripts.benchmark_pipeline_profiles --profile light --device cuda:0 --api-url http://127.0.0.1:38000 --rounds 1 --output .evaluation-tmp/gold-v3-light-gpu-pipeline.json
docker compose -f compose.yaml --env-file infrastructure/demo.env.example -p aegis-gold-v3 --profile full down
```

These are public local development credentials. Tokens/private keys stay out of logs/Git.
Only the local worker encrypts during this benchmark; copied nonce allocators are not a
safe general multi-writer arrangement. Never overwrite used nonce state. Stop without
`-v` to retain keys, counters and database evidence. Keep the Docker worker stopped so
it cannot consume the benchmark queue.

One cold plus one warm five-document batch per profile includes complete workflow and
storage/provenance. The runner checks fresh document counts, persisted exact pretrained
models, actual CUDA device placement, verification and duplicate stability. An aborted
run is diagnostic evidence, not a timing; inspect pending work before measuring cold again.

## Presentation artifacts

```powershell
.venv-light/Scripts/python.exe -m scripts.compare_gold_v3
```

This regenerates tables/figure from committed final reports and rejects material device
differences. It does not rerun inference or edit labels. [Results and limitations](gold-v3-gpu.md).

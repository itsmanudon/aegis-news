# Reproducible local demo (5–8 minutes)

Build/seed before presenting. A cold image/model-free build can take minutes and is
not included in the presentation duration. Run from the repository root.

```sh
python scripts/demo.py reset
python scripts/demo.py token --role admin
```

Reset removes only the fixed `aegis-demo` project's local containers/volumes, including
old keys, and recreates five known synthetic articles. Other projects remain untouched.
It refuses remote contexts/hosts. Ordinary `start` and `seed` are idempotent. New UUIDs/
availability times reflect actual persistence; reset does not fabricate historical knowledge.
Copy tokens privately into the UI; do not paste them into public evidence.

## Presentation timeline

| Time | Action and evidence |
|---|---|
| 0:00–0:30 | State problem and open real dashboard at localhost:33000. Explain source vs model output. |
| 0:30–1:00 | Admin identity; show scopes/source operations. Switch to viewer and demonstrate disabled write plus real 403. Generate fresh tokens with `token --role ...`. |
| 1:00–1:45 | Select seeded source. Run `python scripts/demo.py benchmark` once after reset: real batch submission includes PNG media. Show source/workflow/document IDs. |
| 1:45–2:30 | Temporal UI localhost:38233: completed ingestion and its activity history. MinIO localhost:39001: raw/media objects, then normalized article detail. |
| 2:30–3:30 | Show entities, topics, sentiment, events, immutable model/configuration IDs and distinct published/available times. Search Atlas; similarity API is available, UI is not implemented. |
| 3:30–4:15 | Media metadata and explicit signed association. Open original PNG next to the article; dashboard inline preview is explicitly unavailable. Verify provenance. |
| 4:15–5:00 | Run `python scripts/demo.py security --hold-tamper-seconds 25`. During the controlled raw-object change click Verify integrity: failure. After automatic restoration verify again: success. Terminal also proves AES/signature mutation rejection. |
| 5:00–6:00 | Refresh admin token if needed; audit page shows denied requests and failed/successful integrity checks. |
| 6:00–7:00 | Grafana localhost:33001 `/d/aegis-demo`; request/latency panels and correlated Loki worker logs. Prometheus localhost:39090; OTel receipt in collector logs. |
| 7:00–7:30 | Show measured assessment table, typed NER weakness and optional profiles not run; state limitations/future work. |

Development tokens expire after five minutes. Refresh at a role change/around minute five;
do not extend issuer semantics for the demo. MinIO and Grafana use local dummy credentials
`aegis_dev` / `aegis_dev_only`. They are not production secrets or recommended deployment credentials.

## Optional reliability/deeper demo

```sh
python scripts/demo.py reliability
python scripts/demo.py acceptance
python -m scripts.demo_observability
```

Reliability stops only this project's worker, submits a fresh uniquely keyed item,
proves Temporal remains RUNNING, restarts the worker in `finally`, then waits for signed
completion. Repeatable runs create one explicitly new recovery item each. Duplicate
seed submissions reuse workflow IDs and do not add documents/analyses/outbox messages.
The separate real Temporal test injects failure after committed analysis persistence,
stops/restarts its worker, and confirms one document/six analyses/stable outbox.

The acceptance command runs the original 22-control full-stack scenario. Reports are
written to ignored `.integration-results/`; committed evidence snapshots are in
`docs/evidence/`. Tampering occurs only on selected original synthetic demo records.
Graceful errors restore content; if a process is forcibly killed during the hold, reset
the isolated project. Avoid presenting while unrelated scripts modify the same records.

## Platform/start/stop

Windows: `python scripts/demo.py start`, `pnpm.cmd`; PowerShell environment syntax is
`$env:NAME='value'`. macOS/Linux: `python3 scripts/demo.py start`, `pnpm`, `export NAME=value`.
GNU Make wrappers (`make demo-reset`, `demo-seed`, `demo-security`, `demo-benchmark`,
`demo-reliability`, `demo-observe`) use python3 and are optional.
Docker-only equivalents are in the README. No manual database surgery is required.

`python scripts/demo.py stop` retains volumes; `reset` deliberately deletes demo state.
If a port is occupied, change only `infrastructure/demo.env.example` and corresponding
browser/observability test URLs. Do not stop unrelated projects to free ports.
Original integration remains separately reproducible via `infrastructure/mvp.env.example`.

## Browser/screenshot reproduction (PowerShell)

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd --filter @aegisnews/web exec playwright install chromium
$env:AEGIS_E2E_TOKEN = (docker compose --env-file infrastructure/demo.env.example -p aegis-demo exec -T api python scripts/security_dev.py token --key-id local --role admin --subject browser-demo).Trim()
$env:AEGIS_E2E_VIEWER_TOKEN = (docker compose --env-file infrastructure/demo.env.example -p aegis-demo exec -T api python scripts/security_dev.py token --key-id local --role viewer --subject browser-viewer).Trim()
$env:AEGIS_E2E_EXTERNAL_SERVER = '1'
$env:AEGIS_LIVE_E2E = '1'
$env:AEGIS_CAPTURE_EVIDENCE = '1'
$env:AEGIS_E2E_BASE_URL = 'http://127.0.0.1:33000'
$env:AEGIS_E2E_API_URL = 'http://127.0.0.1:38000'
pnpm.cmd --filter @aegisnews/web exec playwright test e2e/live.spec.ts e2e/evidence.spec.ts --workers=1
```

On macOS/Linux use `export AEGIS_E2E_TOKEN="$(docker compose ... token ...)"` with the
same complete Compose arguments above and `pnpm`. Both live tests disable trace capture;
input clears after token use. JPEG screenshots are optimized and contain only synthetic
content/IDs and roles. Do not capture real credentials in browser traces/screenshots.

## Observability evidence

`python -m scripts.demo_observability` checks Prometheus API up, provisioned Grafana
dashboard, Loki correlation/trace IDs and collector receipt. In Grafana use:
`{service="aegisnews"} | json | correlation_id="aegis-demo-v1"`.
Filter `logger="aegis.worker"` for processing and match trace IDs across activity logs.
Temporal provides workflow/activity identity. The seed batch deliberately shares one
correlation group; individual workflow IDs distinguish items. No high-cardinality metric
labels were added. The collector debug-exports traces; there is no durable trace UI.

```sh
docker compose --env-file infrastructure/demo.env.example -p aegis-demo logs --tail 100 otel-collector
```

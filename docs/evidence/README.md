# Reproducible demonstration evidence

Snapshots are from original synthetic data on the isolated Phase 6 full stack.
JPEG screenshots use 1440×1000 viewports and quality 70; private token fields clear
after use and live browser tracing is disabled. No real article dumps, keys or tokens
are included. Fixtures/reports are public-safe; generated IDs/timestamps vary after reset.

| Evidence | What it demonstrates |
|---|---|
| [Dashboard](screenshots/dashboard.jpg) | Real API document feed and acquisition/availability |
| [Document intelligence](screenshots/document-intelligence.jpg) | Typed immutable model outputs |
| [Entity evidence](screenshots/entity-evidence.jpg) | Curated identity and linked documents |
| [Events](screenshots/events.jpg) | Materialized event view |
| [Verification](screenshots/provenance-verification.jpg) | Live successful provenance verification |
| [Media](screenshots/media-links.jpg) | PNG metadata/hash and explicit document association |
| [Scope denial](screenshots/scope-denial.jpg) | Viewer writes disabled; accompanying real request returned 403 |
| [Audit](screenshots/audit-log.jpg) | Persistent security actions without credentials |
| [Temporal](screenshots/temporal-workflows.jpg) | Actual workflow history, not a mock |
| [Grafana/Loki](screenshots/grafana-loki.jpg) | Provisioned metrics/log dashboard |

Raw evidence: `pipeline-benchmark.json`, `security-demo.json`, `observability.json`,
`recovery-submission.json`, `recovery-completion.json`. Each is bounded synthetic evidence,
not general quality/capacity/security certification. AI reports live in `ml/evaluation/results/`.
The demo benchmark is a five-item sample, not a production load test. Snapshot memory
statistics, if included, are point-in-time values rather than measured peaks.

Reproduce with the commands in [demo-guide](../phase6/demo-guide.md). Screenshot capture
also runs assertions against real endpoints; failures are not photographed as successes.

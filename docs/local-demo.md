# Local demo

Run the complete Aegis News product on this machine. The demo uses Real API mode,
local Docker services, original synthetic records and the existing development-token
issuer. It does not deploy anything and it does not need a paid provider.

## Prerequisites

- Python 3.12 or newer
- Docker Engine with Compose v2, using the `default` or `desktop-linux` local context
- A free local port set from `infrastructure/demo.env.example`
- Optional: Doppler CLI, already authenticated, with one unambiguous Aegis News development or demo configuration
- Optional browser smoke: pnpm and Playwright Chromium

Windows, macOS and Linux share `python scripts/demo.py`. On Windows the helper
uses `pnpm.cmd` for the browser smoke. GNU Make is not required.

## First-time startup

From the repository root:

```sh
python scripts/demo.py start --build
```

The first run builds images, starts the full Compose profile, waits for readiness,
and seeds data. A cold build often takes several minutes and can take longer when
Docker must pull base images. Later starts reuse images and stored data.

Ordinary restart, without rebuilding and without deleting data:

```sh
python scripts/demo.py start
```

`start` is safe to repeat. It does not run `docker compose down --volumes`, does
not rotate development keys that already exist, and does not insert a second copy
of a seeded article. Use `--basic` to seed only the original five articles.
Use `--build` after application code changes.

## What startup does

The command checks Python, Docker, Compose and the local Docker context, then
refuses occupied ports that are not already published by the `aegis-demo` project.
It starts PostgreSQL, Redis, MinIO, Temporal, the worker, one-shot key and
migration tasks, the secured API, the Next.js frontend, Prometheus, Grafana, Loki,
Alloy and the OpenTelemetry collector. It waits until required checks pass, seeds
through the real ingestion API, and prints local URLs. A frontend response alone
is not treated as ready.

## Real API and mock mode

The demo image is built with `NEXT_PUBLIC_DATA_MODE=real` and
`NEXT_PUBLIC_API_URL` pointed at the host-mapped API port, `http://localhost:38000`
by default. The browser calls that loopback address. CORS allows only
`http://localhost:33000` and `http://127.0.0.1:33000`. Real API failures stay on
the screen with a retry action. They are not replaced by mock records. The Data
Mode control can still be switched to Mock Development Data for a fictional
workspace.

## Development tokens

```sh
python scripts/demo.py token --role analyst
python scripts/demo.py token --role admin
python scripts/demo.py token --role viewer
```

Paste the token into **Access Token** and choose **Use Token**. The value stays
in memory for that page session, expires after five minutes, and is not stored in
`localStorage` or placed in the URL. `start` does not print a token. Admin can
create sources and read audit events. Analyst can read and verify. Viewer can
read but cannot verify or create sources.

## Doppler and providers

Startup works with no Doppler account. On the machine used for acceptance, the
CLI was authenticated and the only Aegis-like project was `aegis-news`, with
configs `dev`, `dev_personal`, `stg` and `prd`. Two development names are
preferred, so discovery is ambiguous and startup stays offline. Staging and
production names are rejected. If the CLI is authenticated and exactly one
Aegis News development, demo or local configuration is visible, the launcher
injects only these API-container variables when they are non-empty:

- `AEGIS_NEWSDATA_API_KEY`
- `AEGIS_GNEWS_API_KEY`
- `AEGIS_NEWSAPI_API_KEY`
- `AEGIS_YOUTUBE_API_KEY`

Set both `AEGIS_DOPPLER_PROJECT` and `AEGIS_DOPPLER_CONFIG` when discovery is
ambiguous. Production and staging names are rejected. Doppler cannot replace the
local database, Redis, MinIO, Temporal, OIDC or Compose identity. Missing keys
leave that provider unconfigured.

Provider calls are separate and bounded:

```sh
python scripts/demo.py acquire --provider gdelt --limit 2 --confirm
```

GDELT needs no key. The other providers need a configured key. The limit is 1 to 5.
Startup, seeding and the browser smoke do not call providers.

## Demo data

The presentation source `CC0 presentation demo v1` starts from five original
synthetic articles and an original PNG. The showcase source `CC0 showcase demo v1`
adds 24 original synthetic articles across the supported topic labels, with one
unknown publication date and one original media reference. Every showcase text
identifies itself as a synthetic demonstration record, not current news.
Processing goes through Temporal, persisted analyses and signed provenance.
Existing volumes are left in place: a machine that already holds a historical
corpus keeps those documents, and a repeated start does not insert another copy.
On the acceptance machine the presentation source already contained 12 documents
and the 2020 analytics window counted that wider corpus. Reset is the only
command that deletes this project's volumes, and it requires `--yes` or the typed
phrase `reset aegis-demo`.

For analytics, set the publication window to 2020-01-01 inclusive through
2021-01-01 exclusive. The default last-30-days publication window is empty because
the corpus is historical. First Seen uses ingestion time and therefore includes a
freshly seeded corpus.

## Service URLs

| Service | URL |
| --- | --- |
| Web | http://127.0.0.1:33000 |
| API | http://127.0.0.1:38000 |
| API docs | http://127.0.0.1:38000/docs |
| Temporal | http://127.0.0.1:38233 |
| MinIO console | http://127.0.0.1:39001 |
| Prometheus | http://127.0.0.1:39090 |
| Grafana | http://127.0.0.1:33001/d/aegis-demo |
| Loki | http://127.0.0.1:33100 |

MinIO and Grafana use the local dummy account `aegis_dev` / `aegis_dev_only`.
The collector listens on `127.0.0.1:34318` and debug-exports traces. There is no
trace UI.

## Health, logs, shutdown and reset

```sh
python scripts/demo.py status
python scripts/demo.py doctor
python scripts/demo.py logs --service api --tail 80
python scripts/demo.py smoke
python scripts/demo.py stop
python scripts/demo.py reset --yes
```

`status` and `doctor` report component state. Unverified checks are named rather
than marked passed. `logs` prints a bounded, redacted tail for one demo service
or the whole project. `stop` removes only `aegis-demo` containers and keeps
volumes. `reset` refuses a remote Docker context, an external volume, or a
container whose Compose project is not `aegis-demo`.

## Troubleshooting

- Docker missing or a remote context: start Docker Desktop or the local engine, then rerun. The helper will not switch contexts for you.
- Port in use by another project: change `infrastructure/demo.env.example` or stop that other project yourself. This launcher does not stop foreign containers.
- Seed still running: ingestion waits for Temporal completion. Repeat `start` after the worker is up; completed idempotency keys are reused.
- A new workflow can fail once when the Temporal clock is ahead of the worker and `first_seen_at` is rejected as future. Rerun `start`. The check stays in place, and a failed run is not reported as success.
- The collector port answers, but a plain HTTP GET is not a health check. `doctor` leaves `otel-http` unverified.
- Empty analytics: apply the 2020 publication window described above.
- Token rejected: generate a fresh token. Five minutes is the existing lifetime.
- Provider not configured: that is the offline default, not a startup failure.

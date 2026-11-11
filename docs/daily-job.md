# Daily news job

`python -m aegis.jobs.daily` fetches news, ingests, analyses and signs it, then exits. It
is built to run once a day as a cron container with no persistent disk. The owner chose
this design (option B in the workspace note `phase-0-hosted-ingestion-path.md`) on 11 Nov
2026.

## What one run does

1. Starts a throwaway Temporal development server from the Temporal CLI, in memory, on a
   free local port. The image carries a pinned CLI (`infrastructure/docker/job.Dockerfile`);
   the job never downloads one.
2. Starts the normal worker in the same process. `apps/worker/main.py:build_worker` builds
   it for both the long-running worker and the job, so they cannot drift.
3. Runs the provider runner for `AEGIS_JOB_PROVIDERS`. Articles go straight to ingestion
   and to `NewsIngestionWorkflow`, with the same checks the API route makes, instead of
   through the API over HTTP. Every article gets the workflow's retries (five attempts,
   backoff from 1 to 30 seconds).
4. Waits for every workflow, records each finished article against its document, prints
   a JSON report and shuts the server down.

Exit code 0 means every provider it asked for ran (or had spent its daily budget) and
every workflow finished. Anything else exits 1. A crash prints only the exception type,
because provider and key errors can carry secrets.

## Repeat and interrupted runs

The Temporal server forgets everything when it stops, so all state is in Postgres and the
object store:

- An article already turned into a document is not submitted again.
- An article an interrupted run left without a document is submitted again. Its workflow
  identity, analysis identities and provenance identity are derived from the article, so
  the repeat writes nothing new.
- The provider budget (`AEGIS_PROVIDER_DAILY_REQUESTS`) is counted in Postgres, so it holds
  across runs on the same day.

`tests/integration/test_daily_job.py` covers a first run, a repeat run and a run after an
interruption. It needs the Temporal CLI on the `PATH` or in `AEGIS_TEMPORAL_CLI`.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `AEGIS_JOB_PROVIDERS` | `["newsdata"]` | Providers to fetch. Each needs its key, except GDELT |
| `AEGIS_JOB_QUERY` | `stocks OR markets OR earnings` | Provider query |
| `AEGIS_JOB_LIMIT` | `10` | Articles per provider per run, 1 to 30. NewsData.io returns 10 per page |
| `AEGIS_JOB_COUNTRY` | none | `in` or `us` |
| `AEGIS_JOB_TIMEOUT_SECONDS` | `1200` | How long to wait for the workflows |
| `AEGIS_TEMPORAL_CLI_PATH` | `temporal` | The CLI to start |
| `AEGIS_PROVENANCE_SIGNING_KEY` | none | Ed25519 private key as PEM. When set, the job writes it to a private temporary directory for the run |
| `AEGIS_PROVENANCE_KEY_ID` | `local` | Key identifier written into each signed manifest |
| `AEGIS_S3_ADDRESSING_STYLE` | `path` | `virtual` for Railway buckets, `path` for MinIO |

The job always turns off the encrypted provenance archive
(`AEGIS_PROVENANCE_ARCHIVE_ENABLED`), because it needs a nonce counter kept between runs.
The signed manifest does not depend on it.

It also needs `AEGIS_DATABASE_URL`, the `AEGIS_S3_*` settings and `AEGIS_AI_PROFILE`
(`offline` for now). Run `alembic upgrade head` before the first run. The job does not
migrate.

## Railway bucket

Railway buckets are S3-compatible and use virtual-hosted URLs. From the bucket's
Credentials tab set `AEGIS_S3_ENDPOINT_URL` (for example `https://t3.storageapi.dev`),
`AEGIS_S3_ACCESS_KEY`, `AEGIS_S3_SECRET_KEY`, `AEGIS_S3_BUCKET`, `AEGIS_S3_REGION=auto`
and `AEGIS_S3_ADDRESSING_STYLE=virtual`. This was read from Railway's documentation and has
not been tried against a real bucket.

## Measured locally

On 11 Nov 2026, in the job image on an arm64 Mac, against the baseline Postgres and MinIO:

- The image is 520 MB, against 379 MB for the API image. The Temporal CLI is the difference.
- A run with no provider key starts the server, reports the provider disabled and exits 1
  in about 2 seconds.
- The integration test (three runs of two synthetic articles each, `offline` profile)
  passes in about 4 seconds.

No real provider was called. Memory and run time on Railway are still to be measured.

# Historical development corpus

AG News populates the **real local API/dashboard** for development of search,
intelligence views and workflow reliability. It is not Gold evaluation data, a
representative news benchmark, production coverage or human-verified intelligence.
[Gold v3](../../ml/datasets/gold/README.md) remains the evaluation reference.
Measured smoke/load results and UX observations are in the [load ledger](historical-corpus-results.md).

## Corpus and distribution

The [AG News CSV readme](https://github.com/mhjabreel/CharCnn_Keras/blob/master/data/ag_news_csv/readme.txt)
describes version 3 (2015), with 120,000 training records and four categories:
World, Sports, Business and Sci/Tech. Each row supplies category, headline and
description, not a guaranteed full article. The underlying corpus was gathered
beginning in 2004. The readme permits research and other non-commercial activity;
it does not grant a blanket CC0/commercial redistribution license for publisher text.
Use only for local non-commercial academic development; review rights before any
other use. No downloaded articles, converted text or runtime receipts are committed.

The loader pins the CSV mirror at commit
`03836ce08fce38daac53e9b4255ef16e0b9f6303` and verifies SHA-256
`76a0a2d2f92b286371fe4d4044640910a04a803fdd2538e0f3f29a5c6f6b672e`.
The file is 29,470,338 bytes. Downloads are reused and a changed cache is rejected.
All corpus files live in ignored `.data/historical/ag_news/`, also excluded from
Docker contexts. Models, Gold datasets and release tags are unaffected.

## Start and load

Run from the repository root with Docker, Python 3.12+ and uv installed:

```sh
uv sync --frozen
python scripts/demo.py start
uv run python -m scripts.load_historical_corpus --limit 10
uv run python -m scripts.load_historical_corpus --limit 100
uv run python -m scripts.load_historical_corpus --limit 3000 --batch-size 20 --concurrency 2
```

The default is 3,000 valid unique records, batches of 10 and **one concurrent batch**.
`--concurrency 1|2|4` bounds simultaneous batches; maximum outstanding work is
`batch-size * concurrency`, not an unbounded task flood. Batch size cannot exceed
the existing API's 20-record limit. Requests are spaced to at most 12/second, with
backoff for transient transport/5xx/rate-limit errors. Polling defaults to two seconds.
The measured 100-item prefix should pass before increasing concurrency or volume.

```sh
uv run python -m scripts.load_historical_corpus --limit 1000
uv run python -m scripts.load_historical_corpus --limit 5000 --batch-size 20 --concurrency 2
uv run python -m scripts.load_historical_corpus --limit 100 --csv path/to/local-ag-news.csv --data-dir .data/historical/custom-ag-news
```

`--csv` reads an AG News-format local CSV without downloading. A different CSV hash
requires a separate data directory/checkpoint. Selection is a stable prefix of valid
unique rows, with original one-based CSV ordinals retained; no balancing or sampling
claim is made. The scan counts available records beyond the requested prefix without
ingesting them. Empty/malformed, invalid UTF-8, oversized and exact duplicate rows are
skipped with ordinal/reason receipts. Exact article duplicates ignore source category.

## Existing processing and security

The loader uses the existing historical-record validator and deterministic workflow
identity helper, then **only HTTP APIs**: sources, bounded ingestion batches and
workflow status. It never calls persistence repositories, creates analyses itself,
connects directly to Temporal or inserts into PostgreSQL. The existing worker owns
normalization, immutable analyses, permitted materialization, signed provenance,
encrypted archive storage and outbox staging.

The supported `aegis-demo` worker runs **offline**, without downloads or GPU. The loader
does not change worker profiles or reanalyze existing documents. Baseline NER/events
often abstain (`NoPredictions`); workflow completion does not imply every optional
analysis produced output or that intelligence is correct. Reports separate unavailable
stages. Unresolved names remain mentions/model output; no canonical entities are invented.
No Light/Full sweep or reanalysis system is included.
Offline similarity uses hash vectors; neighbors demonstrate wiring, not pretrained semantic quality.

One dedicated source is reused: **AG News Historical Development Corpus**. Its URL
identifies the dataset, not individual publishers. Titles/descriptions are converted to
article JSON with `language: en`, `published_at: null`; no dates, article URLs or authors
are invented. Categories are kept in local `metadata.jsonl`, never inserted into article
text or model outputs. `articles.jsonl` contains only the existing article contract.

Development admin tokens are generated via the supported Docker issuer, kept in memory
and refreshed before their five-minute expiry. Authentication/scopes remain enabled.
`--token-env AEGIS_CORPUS_TOKEN` can consume an existing token from the environment;
the user must refresh such externally supplied tokens. Tokens are never CLI arguments
or report fields. The loader accepts only loopback API addresses.

## Resume, reports and cleanup

Rerun the same command after Ctrl+C, worker interruption or timeout. Keys include corpus
version, split, **full CSV SHA-256** and original ordinal; increasing the limit preserves
prefix identities. The API/workflow is the source of truth: even checkpointed completion
is rechecked. Existing completed/running workflows are reused; failed workflows can be
resubmitted under the existing failed-only workflow reuse policy. No old analyses are updated.

Atomic `state.json` checkpoints bind source, dataset and API URL. Do not run two loaders
against the same checkpoint directory simultaneously. A new/missing checkpoint can still
reuse the source/workflows through the API. Source creation lacks its own idempotency
contract, so its POST is never blindly retried after an uncertain response; rerun to
look up the source by name, or pass `--source-id` if multiple matches exist.

`load-report.json` records counts, elapsed load time, new-record throughput, API response
latencies/retries, optional-stage availability and failed/pending workflow IDs. Progress
is printed about every 15 seconds. `completed` includes existing records; `submitted`
counts this run's accepted new/restarted submissions. They are not additive. Pending
counts include not-yet-attempted selected records. Transport failures do not fabricate
success. Inspect reports and rerun unresolved records; server workflow retries remain
independent. Keep reports local: they can contain record/document identifiers.

Deleting the local corpus cache/checkpoint does **not** delete API documents or MinIO
objects. `python scripts/demo.py reset` deletes **all** data/keys/volumes in its isolated
demo project, including corpus and pre-existing demo data; it is not a corpus-only delete.
Do not reset just to resume. After an intentional stack reset, use a new local checkpoint
directory because the old source/UUIDs no longer exist. No bulk-delete endpoint is added.

## Inspect the frontend

Open <http://localhost:33000> in **Real API** mode. Generate a fresh token:

```sh
python scripts/demo.py token --role admin
```

Paste into **Access token**, choose **Use token**, and search a headline from local
`articles.jsonl`. Select the corpus source to distinguish it from synthetic demos.
Inspect intelligence and **Verify integrity**; browse Entities and Events. Sources
contain dataset metadata, while analyses remain independently derived model output.

The current client assembles the entire feed and requests intelligence per document,
even though the API uses cursor pagination. Thousands of rows can cause substantial
latency, payload and rate-limit pressure, especially on the dashboard/unfiltered feed.
Use a specific search to inspect corpus documents. This task records observations rather
than redesigning pagination, loosening security limits or silently enabling mocks.

## Validation

```sh
uv run pytest -q tests/unit/test_historical_corpus.py
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run python scripts/scan_secrets.py
```

Normal CI tests conversion/limits/duplicate filtering, mocked download integrity,
bounded batches, retry/resume and progress. It never downloads news or models.
`apps/web/e2e/historical-corpus.spec.ts` is opt-in with `AEGIS_HISTORICAL_E2E=1`,
`AEGIS_E2E_EXTERNAL_SERVER=1`, `AEGIS_E2E_BASE_URL`, an environment-only `AEGIS_E2E_TOKEN`,
`AEGIS_HISTORICAL_SOURCE_ID` and `AEGIS_HISTORICAL_TITLE`; traces are disabled to protect tokens.

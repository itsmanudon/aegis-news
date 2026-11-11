# Incremental document feed

`GET /api/v1/feed/documents` lets a downstream service copy signed documents on a
schedule, taking only what changed since its last call. It was added for StockViz's
nightly sync. The route is additive: no existing route or record changed.

## Position and availability

A document enters the feed when its first provenance manifest is signed. Two stamps on
the `documents` table record this, written by `AnalysisPipeline.sign` in the signing
transaction:

| Column | Meaning | Changes |
| --- | --- | --- |
| `available_at` | When the first signed run completed. This is when Aegis made the document available. | Never |
| `last_signed_at` | When the latest signed run completed. Equal to `available_at` until the document is analysed again. | On every later signed run |

The feed is ordered by `(signed_xid, document_id)` ascending, where `signed_xid` is the
id of the transaction that signed the document last. A row is returned only once every
transaction with a lower id has ended, so a signing transaction that commits late holds
the feed back until it commits, and is never skipped. Clocks play no part. A document that
is analysed and signed again moves forward and is returned once more, with its new
analyses, so a consumer that upserts by `document_id` stays current.

Cursors issued before 11 Nov 2026 were positioned by `last_signed_at` and are refused with
422. Start again with `since`.

**A bundle is the document as of its latest signed run.** It carries only the analyses
that run signed, and the instruments and events that follow from them. Analyses from an
earlier run, and analyses no run has signed yet, are left out. A consumer replaces what
it holds for the document; an instrument link or event missing from the new bundle is
gone. The `manifests` list still covers every run, oldest first, so the last entry is
the run the bundle describes. One gap remains: the instrument filter (`scheme`, `venue`,
`identifier`) matches a resolution from any run, so a filtered page can return a
document whose latest run no longer links to that instrument.

A document that was never signed is not in the feed.

The stamps are not part of the canonical `NewsDocument` record. That record is hashed
into the signed manifest, so a field written after signing would make verification
fail. Routes that return `NewsDocument` are unchanged.

## Request

Scope: `feed:read`. It reaches this route and `GET /api/v1/assets/mappings` only, so a
consumer that syncs the feed holds no scope for article text. `documents:read` and
`events:read` do not open the feed. See `docs/security-crypto.md` for minting a service
token.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `limit` | integer, 1 to 100 | 50 | Page size |
| `cursor` | opaque string | none | Resume position: a `resume_cursor` or `next_cursor` from an earlier response |
| `since` | timestamp with offset | none | Only documents last signed at or after it, when there is no cursor. Inclusive. |
| `mapped` | boolean | false | Only documents linked to at least one instrument |
| `scheme`, `venue`, `identifier` | string | none | Only documents linked to a matching listing. Each implies `mapped`. `venue` is a MIC code. |

Give `cursor` or `since`, not both. With neither, the feed starts from the beginning.
A cursor belongs to the filters it was issued with; sending it with different filters
returns 422.
An invalid cursor, a timestamp without an offset, or both parameters together return
422 with `INVALID_ARGUMENT`.

## Response

```json
{
  "data": [
    {
      "document": {},
      "source": {},
      "analyses": [],
      "instruments": [],
      "events": [],
      "manifests": []
    }
  ],
  "as_of": "2026-11-10T14:03:40Z",
  "pagination": {"has_more": false, "next_cursor": null},
  "resume_cursor": "opaque",
  "meta": {"request_id": "opaque-id", "api_version": "v1"}
}
```

- **`resume_cursor`** is always present, also on an empty page. Store it and send it as
  `cursor` on the next sync. When `has_more` is true, `next_cursor` holds the same value.
- **`as_of`** is the request time. Analyses, events and mappings are read as of it.
- **`document`**: identifiers, `title`, `url` (the ingestion's source URL), `language`,
  the publisher's `published_at`, `first_seen_at`, `ingested_at`, `created_at`,
  `available_at`, `last_signed_at` and `revision`. There is no `text`.
- **`source`**: the canonical `Source` record.
- **`analyses`**: canonical `AnalysisResult` records of type `topic`, `sentiment` and
  `entity_resolution`, each with provider, model name, model version, configuration
  hash and its own `available_at`. Ordered by `available_at`, then `analysis_id`.
- **`entities`**: every entity the document resolved to, mapped to a listing or not, with
  its name, kind, the resolving analysis and the best resolution confidence.
- **`instruments`**: one entry per asset mapping of an entity the document resolved to,
  with the mapping's scheme, identifier and venue, the resolving analysis and the best
  resolution confidence. Entities with no mapping are not listed. A filtered feed still
  returns all of a document's instruments, not only the matching one. How entities and
  mappings are seeded and matched is in [instruments.md](instruments.md).
- **`events`**: identifier, revision, `event_type` and `confidence` from the extraction
  that produced the event, `occurred_at`, `available_at` and the analysis identifier.
- **`manifests`**: the hash, key identifier and signing time of each signed manifest
  that covers the document, oldest first.

## Withdrawals

Aegis never ingests a known article again, and the free provider tiers send no
corrections or retractions. When a document must go (a publisher takedown, wrong
content), the owner withdraws it:

    python -m aegis.jobs.withdraw DOCUMENT_ID --reason "publisher takedown"

The document moves forward in the feed and is delivered once more as a tombstone:
`withdrawal` carries `withdrawn_at` and `reason`, and `analyses`, `entities`,
`instruments` and `events` are empty. A consumer deletes what it holds for that
document. Every other bundle has `withdrawal: null`. Aegis keeps the rows and the signed
manifests. Other read routes, such as `/api/v1/documents`, still return the document.

## Instruments added later

The cursor moves on signing time, and seeding a mapping does not touch documents. So a
mapping added after a document was delivered never brings that document back, and a
consumer using `mapped` or a listing filter never receives a document that had no mapping
when it was read.

For a sync, read the feed without instrument filters, keep each bundle's `entities`, and
read `GET /api/v1/assets/mappings` whole on every sync (the list is small). Join the two
locally. A new mapping then applies to every document already held. The `instruments`
field and the filters stay for one-off reads.

## Verifying a bundle offline

Two more routes under the same `feed:read` scope:

- `GET /api/v1/feed/keys` returns the Ed25519 public key manifests are signed with, as
  `key_id` and PEM. Pin it. A new key id means a rotation.
- `GET /api/v1/feed/manifests/{manifest_hash}` returns one manifest listed in a bundle's
  `manifests`: records of ids and SHA-256 hashes, the chain hashes, the key id and the
  signature. It holds no article text.

`aegis/provenance/consumer.py` is the reference check, written with only the standard
library and `cryptography` so a consumer can copy it. Given a bundle, its latest manifest
and the pinned key, it checks the signature, the hash chain, that the manifest names the
bundle's document, and that every analysis in the bundle hashes to its signed record.
`tests/integration/test_mvp.py` runs it against JSON read through the API.

What it cannot check: the document and the raw content are hashed with their text, which
the feed never sends. The title, URL, source, `available_at`, entities, instruments and
events rest on the authenticated transport.

## What the feed never returns

- Article text, in `document` or anywhere else.
- `entity_extraction` and `event_extraction` analyses, whose outputs quote the article.
- Event `summary`, which is an article excerpt.
- `embedding` analyses.

`tests/integration/test_feed.py` asserts this against a seeded database.

## Point-in-time use

A consumer that must not look ahead should order and filter by `available_at`, never by
`published_at`, and should treat each analysis as known from that analysis's own
`available_at`.

## Migration

`feed_0001` adds the two columns, the `document_feed_position` index and an index on
`signed_manifests.created_at`. It stamps documents that were signed before the
migration from the manifests that already cover them.

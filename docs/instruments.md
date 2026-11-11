# Instruments: entities, names and listings

Aegis links a news document to a tradable instrument in three steps. A model finds
mentions in the text. Resolution decides which curated entity a mention means. Asset
mappings say which listings identify that entity. This page covers the last two.

## Seeding

Entities and mappings are written by a command, not by a route. The list changes
rarely, and a write route would be one more surface to secure.

```sh
python -m aegis.entities.seed instruments.json --dry-run   # validate and report
python -m aegis.entities.seed instruments.json             # write
```

The file is a JSON array. Each item is one entity:

```json
[
  {
    "name": "Example Industries Limited",
    "aliases": ["Example Industries", "EIL"],
    "listings": [
      {"identifier": "EXAMPLE", "venue": "XNSE"},
      {"identifier": "500000", "venue": "XBOM"},
      {"scheme": "isin", "identifier": "INE000A01018"}
    ]
  }
]
```

- **`name`** is the canonical name. **`kind`** defaults to `organization`.
- **`aliases`** are other names the entity is known by in news text.
- **`listings`** are asset mappings. The default scheme is `exchange_symbol`, which
  needs a `venue`.
- **`venue` is an ISO 10383 market identifier code (MIC) from an allow-list**: `XNAS`,
  `XNYS`, `XASE`, `XNSE`, `XBOM`, `XLON`, `ARCX` and `BATS` (`aegis/entities/registry.py`,
  `MICS`). Exchange names, and four-letter codes that only look like a MIC such as
  `NYSE` or `NASD`, are rejected. Add a code to the list, checked against ISO 10383,
  when a new venue is needed.
- An entity listed on two venues is one item with two listings.
- **A listing belongs to one entity.** The database holds scheme, identifier and venue
  unique on their own. A file that gives an existing listing to a different entity
  skips it and names it under `listing_conflicts` in the report.
- **The seed only adds.** A listing stored for an entity in the file that the file no
  longer lists stays, and is named under `listings_not_in_file`. Remove it by hand if
  it is wrong.

The whole file is validated before anything is written, the write is one transaction,
and running the same file again changes nothing. The command prints a report as JSON.
Exit code 2 means the file was rejected.

An entity that already exists under the same name is reused, so seeding can attach
listings to entities that were created earlier.

## How a mention finds its entity

Each name and alias is stored under **match keys** in the `entity_names` table
(`resolution.match_keys`):

| Name | Keys |
| --- | --- |
| `Apple Inc.` | `apple inc`, `apple` |
| `The Coca-Cola Company` | `the coca cola company`, `coca cola` |
| `Reliance Industries Limited` | `reliance industries limited`, `reliance industries` |
| `Meridian Holdings` | `meridian holdings` |

A key is the name lower-cased with punctuation removed. A second key drops a leading
"the" and trailing legal forms such as Inc, Ltd, Limited, Corp, PLC and Pvt. Words such
as "Holdings" or "Group" are kept, because they tell real companies apart.

For each document, the candidates are the entities whose keys equal a key of one of the
document's mentions. That is an index lookup per mention. The cost follows the mentions
in the article, not the number of entities in the table.

The resolver then scores those candidates. A key match scores 1.0, with two exceptions
(resolver revision 3):

- **Kind.** When the extractor says a mention is a person or a location, it never matches
  an organisation, and so on. The offline extractor labels every span `other`, which
  decides nothing.
- **Short names.** A name of four characters or fewer matches only where it appears, as
  whole words and with the same capitalisation, in the entity's name or an alias. `SAP`
  matches `SAP SE`; `Sap` does not.

Names that differ from the legal name ("Amazon" for "Amazon.com, Inc.", "Google" for
"Alphabet Inc.") need an alias in the seed file. `tests/unit/test_entity_registry.py`
holds the disambiguation cases. Precision on real articles has not been measured.

### What stays unresolved, on purpose

- **A key shared by two entities.** If "Meridian" could be Meridian Ltd or Meridian Inc,
  the mention is left unresolved. The seed report lists such keys under `shared_keys`.
  Add a distinguishing alias, or accept that the short name is ambiguous.
- **Tickers.** Symbols identify listings; they are not used to match text. Many are
  ordinary words ("ALL", "IT", "ON"), and matching them would link unrelated articles.
- **Names the extraction model did not find.** Resolution only sees the mentions the
  model produced. Its recall is the ceiling for everything described here.

### Small curated sets

While the entities table holds 1,000 rows or fewer, every entity is also offered as a
candidate, which is how resolution worked before name keys existed. Entities written
without keys (test fixtures, the demo seed) therefore still resolve, and near-miss
spellings can still be scored by similarity. Beyond 1,000 entities only keyed entities
are reachable. The seed command always writes keys.

## Reading mappings

`GET /api/v1/assets/mappings` lists mappings ordered by `mapping_id`. Scope:
`feed:read`.

| Parameter | Meaning |
| --- | --- |
| `limit`, `cursor` | Paging, as on other collections |
| `as_of` | Only mappings created at or before this time |
| `entity_id` | Mappings of one entity |
| `scheme` | `exchange_symbol`, `isin` or `provider_id` |
| `venue`, `identifier` | Exact match |

The incremental feed returns a document's instruments inside each bundle and can filter
by them. See [feed.md](feed.md).

## Limits to know

- **Mappings are timeless.** A mapping has a creation time and no end date. A symbol
  that changes or is delisted needs a new seed file; the old mapping stays.
- **A mapping added later links older documents too.** The link is computed when the
  feed is read. A consumer that must not look ahead should compare its own first-seen
  time for the link, not assume the link existed when the document was published.
- **Resolution is recorded per analysis.** Documents analysed before an entity was
  seeded are not linked to it until they are analysed again.

# Dataset stages

- **raw**: source-authorized original inputs and a license/source manifest. Keep actual article
  dumps outside the public repository; downloading models is separate from ingesting news.
- **silver**: canonical NewsDocument revisions plus model AnalysisResult proposals, retaining
  analysis IDs, providers, immutable versions, configuration hashes and timestamps. Silver is
  model output, not human-verified fact.
- **gold**: human-reviewed task labels with a versioned annotation policy, source permissions,
  train/dev/test separation and document revisions. Gold examples consumed by the CLI use
  `GoldSample` from `aegis.intelligence.evaluation`.

`gold/synthetic.jsonl` contains nine hand-authored synthetic English examples, synthetic candidate
entities and deterministic UUIDs. No real company identity, copyrighted news dump, customer data
or market prices are included. NER gold labels include span offsets and entity kinds; resolution
gold may be null to represent unknown candidates. Gold mentions are manual fixture evidence,
not outputs silently promoted from a model into facts.

To import permissible data, produce JSONL matching `GoldSample`, then run:

```sh
python -m aegis.intelligence.evaluation --dataset /path/to/permitted-gold.jsonl --profile offline
```

The loader validates labels, offsets, candidate identities and unique document IDs. For larger
articles supply an explicit `event_summary` (maximum 512 characters) for event classification.
Archive permission metadata and the dataset digest alongside reports. The public samples are
smoke fixtures, not a benchmark or a representative evaluation corpus.

Reserved foundation boundary. Use synthetic or licensed data only. No model downloads, training, inference, real-user data or dataset dumps in this phase.

## Integrated MVP fixtures

`mvp.json` contains five original synthetic articles and a synthetic text attachment. These samples are dedicated to CC0. Names and events are fictional. Run `scripts/mvp_acceptance.py` in the local Compose API container to seed curated synthetic entities, submit the articles through the authorized API, and verify the workflow.

## Showcase corpus

`showcase.json` adds original synthetic articles for the local demo. Names,
events and dates are fictional. Each text says that it is a synthetic
demonstration record. `python scripts/demo.py start` submits this file through
the normal ingestion API after the five-item presentation set. `--basic` skips it.

## Phase 6 media

`demo-image.png` is an original CC0-1.0 schematic bar illustration generated with
standard-library PNG encoding by `scripts/build_assessment_set.py`. It is not a
news photograph or external artwork. The deterministic demo seed uploads it as a
real image, persists explicit document-media links and verifies its bytes/metadata.
The assessment dataset has a separate annotation/review policy under `ml/datasets/gold/`.

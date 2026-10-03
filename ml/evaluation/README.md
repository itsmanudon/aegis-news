# Evaluation harness

Run from the repository root in an installed project environment:

```sh
python -m aegis.intelligence.evaluation --profile offline --output evaluation.json
python -m aegis.intelligence.evaluation --profile light --dataset ml/datasets/gold/synthetic.jsonl
pytest tests/unit/test_intelligence.py tests/unit/test_ai_adapters.py tests/unit/test_ai_runtime.py tests/unit/test_ai_registry.py -q
```

Light/full require separately installed/downloaded weights; the harness itself never downloads.
Offline needs neither models nor network/GPU/paid APIs. See `ml/models/README.md` for model setup.

Metrics are computed from predictions and gold labels:

- NER exact document/span/kind precision, recall and F1 (micro counts).
- Topics and document sentiment accuracy, micro F1 and macro F1 over observed label union.
- Entity resolution accuracy including explicitly unresolved labels, and top-3 candidate recall
  reported as top-3 accuracy. Resolution is evaluated over gold mentions to isolate resolver quality.
- Existing-event classification accuracy/micro F1/macro F1, using a synthetic/manual event summary
  and retaining its event revision. This is not an event detection benchmark.

Zero denominators yield zero for span metrics; a dataset without resolution mentions reports null
resolution metrics. NoFindings/NoPredictions for NER is recorded and counted as no predicted spans.
Other failures terminate the run rather than being reported as successful predictions. Reports
include a canonicalized dataset SHA256, document revision/text SHA256, each analysis's metadata,
and an explicit warning that synthetic results cannot estimate real-news quality.

No pretrained accuracy numbers are asserted. Running the offline profile on the supplied fixtures
exposes its capitalization-only NER's inability to predict organization types. Extend gold data
with permitted, independently annotated examples and held-out splits before comparing models.
Confidence calibration, multilingual quality, event extraction quality and embedding retrieval
benchmarks remain future evaluation work.

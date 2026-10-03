# Gold v2 CPU comparison

16 synthetic CC0 items; single agent adjudication, independent human sign-off pending.
No production-quality or held-out real-news claim. Delta = Light minus Offline.

| Task | Offline | Light | Delta |
|---|---:|---:|---:|
| NER span precision | 1.0000 | 1.0000 | +0.0000 |
| NER span recall | 0.9412 | 0.9412 | +0.0000 |
| NER span F1 | 0.9697 | 0.9697 | +0.0000 |
| NER typed precision | 0.0000 | 1.0000 | +1.0000 |
| NER typed recall | 0.0000 | 0.9412 | +0.9412 |
| NER typed F1 | 0.0000 | 0.9697 | +0.9697 |
| Topic accuracy | 0.8125 | 0.8125 | +0.0000 |
| Topic macro F1 | 0.6667 | 0.6667 | +0.0000 |
| Sentiment accuracy | 0.5000 | 0.6250 | +0.1250 |
| Sentiment macro F1 | 0.3902 | 0.4908 | +0.1006 |
| Event precision | 0.9000 | 0.9000 | +0.0000 |
| Event recall | 0.7500 | 0.7500 | +0.0000 |
| Event F1 | 0.8182 | 0.8182 | +0.0000 |
| Event classification accuracy | 0.7500 | 0.7500 | +0.0000 |
| Event classification macro F1 | 0.7714 | 0.7714 | +0.0000 |
| Resolution accuracy (gold mentions) | 1.0000 | 1.0000 | +0.0000 |
| Resolution top-3 (including correct abstentions) | 1.0000 | 1.0000 | +0.0000 |
| Retrieval MRR | 0.1987 | 0.8094 | +0.6107 |
| Retrieval recall@3 | 0.1875 | 0.8125 | +0.6250 |

| Profile | Pretrained models | Peak RSS MiB | Snapshot MiB | Median ms | p95 ms | Docs/s |
|---|---|---:|---:|---:|---:|---:|
| offline | none | 38.9 | 0.0 | 3.39 | 4.91 | 281.23 |
| light | BERT NER / FinBERT / MiniLM | 1251.3 | 919.6 | 142.11 | 173.14 | 7.01 |

48 sequential warm seven-task evaluation passes per profile; three rounds of 16 items.
Includes gold-mention resolution and summary classification; excludes storage/Temporal.
RSS sampled every 20 ms includes native allocations; not a guaranteed peak. Disk is
selected model snapshot logical payload, excluding packages, other cached revisions and
filesystem allocation overhead. CPU defaults unchanged; no GPU/VRAM measurement.

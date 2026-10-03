# Gold v3: one independent human reviewer

16 synthetic CC0 English samples; same labels as v2. No production-quality claim.

| Task | Offline Gold v3 | Light CPU Gold v3 | Light GPU Gold v3 |
|---|---:|---:|---:|
| NER span precision | 1.0000 | 1.0000 | 1.0000 |
| NER span recall | 0.9412 | 0.9412 | 0.9412 |
| NER span F1 | 0.9697 | 0.9697 | 0.9697 |
| NER typed precision | 0.0000 | 1.0000 | 1.0000 |
| NER typed recall | 0.0000 | 0.9412 | 0.9412 |
| NER typed F1 | 0.0000 | 0.9697 | 0.9697 |
| Topic accuracy | 0.8125 | 0.8125 | 0.8125 |
| Topic macro F1 | 0.6667 | 0.6667 | 0.6667 |
| Sentiment accuracy | 0.5000 | 0.6250 | 0.6250 |
| Sentiment macro F1 | 0.3902 | 0.4908 | 0.4908 |
| Event precision | 0.9000 | 0.9000 | 0.9000 |
| Event recall | 0.7500 | 0.7500 | 0.7500 |
| Event F1 | 0.8182 | 0.8182 | 0.8182 |
| Event classification accuracy | 0.7500 | 0.7500 | 0.7500 |
| Event classification macro F1 | 0.7714 | 0.7714 | 0.7714 |
| Resolution accuracy | 1.0000 | 1.0000 | 1.0000 |
| Resolution top-3 with abstentions | 1.0000 | 1.0000 | 1.0000 |
| Retrieval MRR | 0.1987 | 0.8094 | 0.8094 |
| Retrieval recall@3 | 0.1875 | 0.8125 | 0.8125 |

| Profile | Device | Cold document ms | Warm median ms | Warm p95 ms | Docs/s | Peak RSS MiB | Peak allocated VRAM MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| offline | cpu | 7.68 | 3.47 | 4.61 | 280.62 | 38.5 | not used |
| light-cpu | cpu | 12965.67 | 140.58 | 182.11 | 7.10 | 1244.0 | not used |
| light-gpu | cuda:0 | 7063.85 | 62.65 | 95.23 | 15.20 | 1544.4 | 974.9 |

Cold is an empty process model cache, not flushed OS disk cache. GPU device setup/import
is reported separately; model load includes remaining imports. Three warm rounds (48
sequential seven-task passes) after one full warmup. RSS sampled every 20 ms; VRAM is
the PyTorch process allocator. No isolated GPU-utilization estimate.
Background workload uncontrolled.

| Pipeline profile | Device | Cold median / p95 ms | Warm median / p95 ms |
|---|---|---:|---:|
| offline | cpu | 3138.27 / 3229.89 | 2643.06 / 2799.65 |
| light-cpu | cpu | 38313.93 / 38369.42 | 2563.79 / 2581.60 |
| light-gpu | cuda:0 | 26058.30 / 26105.56 | 1834.14 / 1900.33 |

Pipeline uses the same five CC0 demo articles/media, not all 16 evaluation cases.
Each profile has one cold and one warm batch, fresh ingestion keys, signature
verification and duplicate checks. With n=5, p95 is the maximum.
Temporal/SQL/storage overhead remains.

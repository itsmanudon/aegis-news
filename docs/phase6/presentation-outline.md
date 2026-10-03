# College presentation outline and viva mapping

This is structured content for a later deck; no final PowerPoint was created.
Use a short narrative plus the 5–8 minute demo, with detailed evidence in an appendix.

| Slide | Content and suggested evidence |
|---|---|
| 1. Problem | Fragmented text/media, unclear model evidence, tamperable records and timing ambiguity |
| 2. Motivation | Analysts need inspectable provenance, scoped access and reproducible processing |
| 3. Existing systems / inspiration | Separate news APIs, NLP pipelines, workflow orchestration and provenance concepts; do not claim comparative experiments or production C2PA |
| 4. Proposed solution | Local secure multimodal news intelligence; what exists now |
| 5. Architecture | Modular monolith/workers diagram; PostgreSQL truth, Temporal, MinIO |
| 6. Multimedia | Original PNG, real MediaAsset and explicit DocumentMediaLink; signed actual bytes/metadata |
| 7. AI | Six tasks/profiles, immutable model/configuration lineage; rules vs pretrained models |
| 8. Information Security | JWT resource-server validation, scoped RBAC, request budgets, audits/redaction |
| 9. Cryptography | Distinguish SHA-256, AES-GCM, Ed25519 and TLS; key/nonce handling |
| 10. Provenance | Raw → document → analyses → derived records → signed chain; live verification |
| 11. Implementation | FastAPI/OpenAPI, TypeScript generated types, transactions, Compose |
| 12. Evaluation | Gold protocol/review status, exact metrics, confusions, poor typed NER/retrieval |
| 13. Security testing | 14-control demo and actual mutation rejection; bounded threat model |
| 14. Demo | Timeline in demo-guide; backup screenshots and JSON reports |
| 15. Results | Working local stack, retries/recovery, measured small-batch latency, validation evidence |
| 16. Limitations | Tiny synthetic set, missing optional models, local adapters, no truth guarantee |
| 17. Future work | Human adjudication/held-out data/local-model experiments; downstream consumers explicitly future |

## Assignment rubric

| Requirement | Completed implementation | Inspectable evidence |
|---|---|---|
| Artificial Intelligence | Extraction, topics, sentiment, resolution, events, vectors; optional local models | `aegis/intelligence/`, gold/report/confusion matrices; no fake pretrained quality |
| Information Security | JWT validation/scopes, bounded ingestion, audits, redaction | Protected-route tests, security-demo JSON, denial screenshot, threat model |
| Cryptography | Standard SHA-256, AES-256-GCM and Ed25519 | Stored encrypted archive, signatures, ciphertext/content mutation rejection, nonce tests |
| Multimedia | PNG + MediaAsset + explicit document association + signed metadata/bytes | Original fixture, media screenshot and tampering test; no CV claim |
| Working prototype | Full real API/Temporal/PostgreSQL/MinIO/dashboard lifecycle | Reset/seed/full demo and hosted/local validation |
| Repository | Public-safe original dataset, contracts, versioned code, frozen release | README, release CI/tag evidence, lockfiles/secret scans |
| Presentation/demo | 5–8 minute script, diagrams, screenshots, structured outline | `docs/phase6/`, `docs/evidence/` |

## Viva answers to keep precise

- Why AI output is not a fact: immutable analyses and producing IDs preserve hypotheses;
  entity resolution is separate and ambiguous mentions remain unresolved.
- Why a valid signature is insufficient alone: also check chain and current raw/SQL/media
  content. A signer can still process false source content.
- Why retries are safe: stable workflow/task identities and transactions, proven by a
  post-commit failure/restart test. A new analysis run creates a new immutable result.
- Why availability differs from publication: knowledge becomes available after acquisition/
  analysis; historical publication cannot be used to leak later intelligence backward.
- Why three crypto mechanisms: hashes detect changes, GCM protects stored confidentiality/
  authenticity, signatures authenticate trusted origin. TLS handles transport separately.
- Why offline evaluation matters: practical CI/reproducibility baseline; measured weaknesses
  are reported. Installed pretrained model weights were not evaluated.
- Why local monolith/workers: complete small-system behavior without unnecessary distributed
  runtime. Outbox delivery/consumers can evolve later without weakening contracts.

Algorithm references are linked in security-and-crypto.md. Avoid unsupported novelty,
accuracy, scalability, nonrepudiation, production-security or fact-checking claims.

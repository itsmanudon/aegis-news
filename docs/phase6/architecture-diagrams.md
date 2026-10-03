# Presentation architecture diagrams

Solid paths exist in the local prototype. The final diagram is explicitly future-only.

## System

```mermaid
flowchart LR
    UI[Next.js analyst console] --> API[FastAPI modules]
    API --> Security[JWT / scopes / audit]
    API --> Temporal[Temporal]
    Temporal --> Worker[Python worker]
    Worker --> PG[PostgreSQL source of truth]
    Worker --> S3[MinIO S3 objects]
    API --> PG
    Security --> Redis[Redis rate limiter]
    PG --> Outbox[Transactional outbox]
    Worker --> OTel[OTel context + JSON logs]
    API --> OTel
    OTel --> Loki[Loki / Alloy]
    API --> Prom[Prometheus]
    Prom --> Grafana[Grafana]
    Loki --> Grafana
```

## Ingestion and Temporal

```mermaid
flowchart TD
    Submit[Authenticated local submission] --> Prepare[Acquire / validate MIME-size / hash / store raw-media / persist ingestion]
    Prepare --> Normalize[Normalize article]
    Normalize --> Commit[Commit document + explicit media links + ingestion outbox]
    Commit --> AI[Retryable intelligence activities]
    AI --> Prov[Sign provenance / encrypt archive]
    Prov --> Query[Product queries / dashboard]
    Failure[Transient activity failure] --> Retry[Temporal retries same workflow/task identity]
    Retry --> Commit
    Retry --> AI
```

## AI pipeline

```mermaid
flowchart TD
    Doc[Normalized NewsDocument] --> NER[Entity extraction]
    Doc --> Topics[Topics]
    Doc --> Sentiment[Sentiment]
    Doc --> Emb[Embedding]
    Doc --> Events[Event extraction]
    NER --> A[Immutable AnalysisResult]
    Topics --> A
    Sentiment --> A
    Emb --> A
    Events --> A
    A --> Mention[EntityMention: model_output / producing analysis]
    Mention --> Resolve[Curated candidate resolution / ambiguity abstention]
    Resolve --> RA[Separate resolution analysis lineage]
    A --> NE[NewsEvent: producing analysis / revision]
    A --> Vector[Compatible-space pgvector similarity]
```

## Provenance and tampering

```mermaid
flowchart TD
    Raw[Raw object bytes] --> Hash[SHA-256]
    Hash --> Doc[Normalized NewsDocument]
    Image[Original PNG + media metadata] --> Link[Explicit DocumentMediaLink]
    Link --> Doc
    Doc --> AI[Immutable AI analyses]
    AI --> Derived[Model-output mentions / events]
    Derived --> Records[ProvenanceRecords: inputs and hashes]
    Records --> Sign[Ed25519 signed canonical chain]
    Sign --> Archive[AES-GCM encrypted stored archive]
    Sign --> Verify[Verify signature / chain / live SQL-raw-media / all analysis runs]
    Tamper[Change raw bytes / SQL text / PNG] --> Verify
    Verify --> Result[Changed content fails / restored content passes]
```

The security demo verifies this live chain, changes controlled raw/SQL/image content,
observes failure, restores it and observes success. For a live UI window use
`python scripts/demo.py security --hold-tamper-seconds 25` and verify the seeded Atlas
article during/after the window. Graceful exceptions restore content; OS kills can
interrupt cleanup, in which case reset the isolated demo. See the [original PNG](../../data/samples/demo-image.png).

## Future consumers — not implemented

```mermaid
flowchart LR
    A[AegisNews API / future outbox delivery] -. future .-> S[Stockwise]
    A -. future .-> B[Backtester]
    A -. future .-> P[Portfolio consumer]
    A -. future .-> L[Live ticker consumer]
```

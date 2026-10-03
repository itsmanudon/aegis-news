# Security boundaries

The security layer implements OAuth2/OIDC validation, RBAC/scopes, cryptography,
signed provenance, audits, and application abuse controls. See
[security integration](security-crypto.md) for configuration and limitations.
Production still requires TLS, external IAM, restricted infrastructure identities,
managed keys, and reviewed deployment configuration.

All source content, uploads and future model outputs are untrusted. Normalize/validate at module boundaries. Contracts reject unknown fields, enforce identifier shapes, aware times, bounded confidence and declared fact/model evidence. Direct database access still requires validation and future restricted roles. The local PostgreSQL owner account exists to simplify migrations and tests, not to model production least privilege.

No production credentials, private keys, real user data, or copyrighted datasets
may enter Git, fixtures, logs, errors, or traces. `.env.example` has dummy local
credentials. Private material, key directories, nonce databases, and caches are
ignored and scanned. SHA-256, AES-256-GCM, and Ed25519 use operational standard
implementations, with no custom cryptographic primitives.

Local Compose uses loopback ports and dummy credentials. Redis, Temporal, Loki, metrics/docs and storage services are local development facilities. TLS, authorization, network policy, restricted database identities and credential rotation must be designed before any non-local deployment. Go appears only in the third-party MinIO image build stage; application backend/worker code is Python. Review upstream MinIO maintenance/security before any production storage choice.

Structured request logs include bounded request/correlation IDs, route templates and trace IDs. They intentionally omit raw input, URLs, exception text/tracebacks and secrets. The OTel request hook redacts URL/query attributes and uses a stable span name; internal ASGI send/receive spans are disabled. IDs are not security credentials. S3 adapter errors propagate internally but readiness/public error handlers sanitize them. The supplied LocalEventPublisher is a no-op and must not be used to assert durable publication or audit completeness.

CI runs dependency audits, the repository secret guard, and redacted Gitleaks.
Secret patterns have no broad credential allowlists. Append-only triggers protect
analyses, security audits, and signed manifests from ordinary SQL mutations;
owners/superusers can bypass these controls. Restrict application database roles
and define controlled privacy deletion/retention separately from migration access.

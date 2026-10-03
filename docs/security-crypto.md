# Security and cryptography integration

The layer implements authentication, authorization, cryptography, internal
provenance, audits, and application abuse controls. Frozen domain records, API
envelopes, events, and foundation schemas remain unchanged. No ingestion, AI,
source editing, user administration, or frontend behavior is implemented.

## Resource server

Set `AEGIS_SECURITY_ENABLED=true`, `AEGIS_OIDC_ISSUER`, `AEGIS_OIDC_AUDIENCE`,
and either `AEGIS_OIDC_JWKS_URL` or `AEGIS_OIDC_PUBLIC_KEYS` (JSON map of kid to
public PEM). JWKS takes precedence. Only configured keys are trusted; token
`jku`/`x5u` URLs are ignored. Allowed algorithms are explicitly RS256/EdDSA.
PyJWT validates signatures, issuer, audience, expiry, issued-at, subject, and
not-before when present. Expiry/issued-at/issuer/audience/subject are required.
Unsigned and shared-secret algorithms are rejected. Errors are generic 401
with Bearer challenge, or 403 for denied permissions.

Default token type is `at+jwt` (RFC 9068). For an issuer using JWT access tokens,
explicitly set `AEGIS_OIDC_TOKEN_TYPES=["JWT"]` only after confirming the API
audience cannot also identify an ID-token client. Do not accept ID tokens.
Roles use a signed `roles` array; OAuth permissions use the space-delimited
`scope` claim. Map provider-specific claims at the issuer. JWKS is cached for
five minutes, with unknown-kid refresh cooldown. Publish rotation keys before
issuing tokens and overlap old keys until expiry. Static keys require reload.
JWKS/signature work runs off the event loop.

Interactive login belongs to an external OIDC provider using authorization code
and PKCE. The API is not an authorization server and implements no password grant.

| Role | Scope ceiling |
| --- | --- |
| admin | all seven scopes below |
| analyst | documents:read, events:read, sources:read, security:verify |
| viewer | documents:read, events:read, sources:read |
| source_manager | sources:read, sources:write |
| security_auditor | audit:read, security:verify |

Known scopes: documents:read, events:read, sources:read, sources:write,
audit:read, security:verify, admin:users. Users need both the delegated scope
and a permitting role. A role does not expand underscoped tokens. Unknown scopes
and roles grant nothing. Use `dependencies=[require_scopes("sources:write")]`;
`authenticate` independently returns an immutable Principal.

Future machine consumers use issuer-managed client credentials, separate clients,
resource audiences, and least privilege. This adapter recognizes signed
`idtyp="app"` plus nonempty `client_id`. Services receive only explicitly delegated
known scopes. The issuer must restrict these claims to registered service clients.
Other issuer conventions require explicit claim mapping. Stockwise and a local
client-credentials server are not implemented.

## Free local demo

A local Keycloak instance can provide realistic interactive OIDC and JWKS without
a paid provider. For fully offline testing, use the isolated JWT fixture issuer:

1. `uv run python -m scripts.security_dev generate --key-id identity-dev`.
2. In ignored `.env`, set `AEGIS_ENVIRONMENT=development`,
   `AEGIS_SECURITY_ENABLED=true`, `AEGIS_DEV_IDENTITY_ENABLED=true`,
   `AEGIS_OIDC_ISSUER=http://localhost:8080`, `AEGIS_OIDC_AUDIENCE=aegisnews`,
   `AEGIS_OIDC_ALGORITHMS=["EdDSA"]`. Configure `AEGIS_OIDC_PUBLIC_KEYS` with
   identity-dev mapped to `.keys/identity-dev.ed25519.pub` contents, escaping PEM
   newlines in JSON. Never place private PEM in API configuration.
3. `uv run python -m scripts.security_dev token --key-id identity-dev --role analyst`.
   This prints a five-minute signed access JWT. Use it as a Bearer token; never
   redirect it into tracked files or logs. Start the API separately.
4. Generate distinct `provenance-dev` material for provenance signing.

The API never mints tokens. Offline issuance requires the explicit dev flag.
Production rejects dev identity and disabled security, requires trusted keys,
HTTPS issuer/JWKS, explicit CORS origins, and Redis rate limiting. The default
disabled security mode preserves local foundation contracts and is rejected in
production. Tests generate keys/tokens dynamically; no committed private fixtures.

## Cryptography and key boundary

StandardCryptoProvider satisfies the existing CryptoProvider with hashlib SHA-256
and PyCA AES-256-GCM/Ed25519. Hashes cover exact bytes for integrity/deduplication;
hashing does not encrypt data or authenticate an origin. AES-GCM protects selected
application data. HTTP transport security remains TLS's responsibility.

EncryptedPayload retains key_id, algorithm, nonce, ciphertext. The nonce is 96
bits; ciphertext includes the trailing 128-bit authentication tag. JSON bytes use
URL-safe Base64. InvalidTag means plaintext must not be released. Internally AAD
is sorted compact UTF-8 JSON of algorithm, key_id, version=1, followed by a zero
byte and caller AAD. Supply document ID, field, and schema version as stable
caller context; reconstruct it on decrypt to prevent ciphertext substitution.

KeyProvider separates key access and durable nonce allocation. Signing/verifying
handles are protocols, allowing remote signing without exporting a private key.
A future KMS adapter can unwrap envelope data keys and provide a distributed
nonce allocator; an HSM can provide a signing handle. Consumers keep their ports.
No KMS/Vault/HSM adapter is implemented.

FileKeyProvider is a development adapter. Keys are exclusively created and never
overwritten. It enforces 32-byte AES and Ed25519 PKCS8/SPKI key types, rejects
traversal IDs and key-file symlinks. POSIX files use owner-only modes. Windows
users must restrict directory ACLs to the developer/service account; POSIX modes
do not enforce Windows ACLs. Separate identity/provenance keys and trust stores.

Encryption commits a monotonic SQLite counter by AES-key fingerprint before use.
Multiple local threads/processes share the allocator; callers cannot select a
nonce. Missing/exhausted state fails closed. Rotate before 2^32 encryptions/key.
Never copy AES material to independent allocators, restore/roll back counter
state, share local material across machines, or clone running VMs with it. Restore
old encrypted backups for decryption only; use fresh keys for new encryption.
Operational duplication/rollback is outside the nonce guarantee. Retain retired
verification/decryption keys while old evidence/data needs them.

## Internal provenance

ProvenanceService signs the frozen ProvenanceRecord values. Begin with operation
raw, no inputs, and the raw-byte hash. Append normalization referencing that raw
subject and hashing normalized bytes. Append derived_artifact referencing the
normalized subject, with analysis_id and artifact hash. Chains reject duplicate
IDs/subjects, missing/forward inputs, and derived artifacts without analysis IDs.

Each chain hash commits to the previous hash and complete current record. Ed25519
signs a versioned manifest containing records, chain hashes, and key ID, encoded as
sorted compact UTF-8 JSON. Verification uses trusted public keys, never keys from
the request. It reports signature_valid, chain_valid, content_verified, valid.
Overall validity requires evidence bytes matching every record; missing content
is not verified. SQLManifestStore persists immutable signed manifests. Production
API wiring supplies it; workers inject it into their own service instances.

A signature proves a trusted key signed declared evidence, not news truth,
publisher authorship, or model accuracy. Analysis IDs are bound references;
referenced analysis outputs are not fetched/independently checked. This encoding
is an internal format, not RFC 8785 or C2PA. Media embedding, publisher trust,
timestamping/revocation, partial proofs, and C2PA are future adapters. Signing is
for trusted application code; there is no public signing/encryption oracle.

## Audit, API, and abuse controls

| Security-enabled endpoint | Permission |
| --- | --- |
| GET /api/v1/security/me | valid bearer token |
| POST /api/v1/security/verify | security:verify |
| GET /api/v1/security/audit?limit=50 | audit:read; latest 1–100 events |

Existing envelopes are reused. Audit retrieval is a latest-events snapshot, not a
history export. Document/entity/search/asset routers get documents:read; events
get events:read. Future write routes need their own write scopes. Sources/admin
routes are not implemented. Health/readiness/system info are public. Restrict
metrics/docs/readiness at the deployment edge if exposed.

Audit actions include authentication success/failure, permission denial, sensitive
document reads, source modification, integrity/signature verification, rate denial,
and admin/security changes. Authentication/denial/verification are wired now.
Future product handlers must emit read/mutation actions with correct outcomes at
the point of action; this branch has no product writes to instrument. Audit
actors/subjects are SHA-256 pseudonyms, not anonymized identities. Extra fields,
tokens, claims, raw request bodies, and secrets are discarded. Audit failure
fails requests closed. Database audit writes are separate transactions; integrate
mutation and audit inserts into one transaction when implementing product writers.

Development audit storage is bounded process-local memory; production uses SQL.
Structured JSON logs include sanitized events, omit exceptions/URLs/bodies, and
redact recognizable bearer/JWT/credential patterns. Never intentionally log secrets;
pattern redaction cannot recognize every credential representation.

Redis atomic Lua INCR/EXPIRE limits peer and validated-identity windows. Peer
checks occur before signature/JWKS work. Outage returns 503; exceeded windows return
429/Retry-After. Peer buckets use the ASGI peer, never blindly trusted forwarding
headers. Shared proxies/NATs share a bucket; configure trusted proxy handling at
deployment. Development uses a bounded in-memory limiter. This is not DDoS
infrastructure. Streamed API bodies are bounded to 256 KiB before JSON parsing.
Configure upstream connection/header limits and timeouts for slow clients.

Responses add nosniff, DENY framing, no-referrer, secure-API no-store, and production
HSTS. CORS allows configured origins and bearer/content headers without wildcard
credential access. Generic errors suppress input/token/internal exception details.
No browser cookie authentication is implemented.

## Migration and validation

security_0001 branches from 0002_contract_hardening with label security, adding
only audit_events and signed_manifests. PostgreSQL statement triggers reject
UPDATE/DELETE/TRUNCATE. Owners/superusers can bypass triggers; give the app only
SELECT/INSERT and keep migration ownership separate. Retention/privacy deletion
needs a controlled privileged process. Existing migrations are unchanged. An
integrator must create a merge revision for any later parallel heads; do not
rewrite this parent.

Run pytest, Ruff format/check, mypy, scripts/export_schemas.py --check, and
scripts/scan_secrets.py. CI also runs dependency audits and Gitleaks. For local
services, migrate a disposable PostgreSQL database, run verify_migrations.py,
then `AEGIS_RUN_INTEGRATION=1 uv run pytest tests/security/test_security_services.py`.
Redis uses a random test bucket; database checks append only synthetic audit events.
CI exercises PostgreSQL append-only behavior and Redis atomic windows. No paid
service is required. Local service tests remain skipped when dependencies are absent.

References: [PyJWT validation](https://pyjwt.readthedocs.io/en/latest/api.html),
[PyCA AEAD](https://cryptography.io/en/latest/hazmat/primitives/aead/),
[RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html).

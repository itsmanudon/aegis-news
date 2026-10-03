# Threat model and cryptography evidence

Scope: local API/worker, PostgreSQL, MinIO, Temporal and development identity. Clients
and content are untrusted; configured issuers, processes and signing-key owners are
trust anchors. Database/object administrators can tamper with evidence. Stolen keys
plus rewritten storage exceed the verification guarantee. This is not a production certification.

| Threat | Impact | Current mitigation | Remaining limitation |
|---|---|---|---|
| Unauthorized API access | Protected read/write | JWT validation; secured route dependencies | System/docs/metrics public locally |
| Privilege escalation | Administrative abuse | Trusted roles bound permitted scopes; signature checked | Issuer/admin/key compromise defeats identity trust |
| Token misuse/replay | Impersonation | Issuer/audience/algorithm/key/time checks; five-minute dev tokens; memory-only shell | No revocation or production browser redirect/refresh |
| Malicious ingestion | Parser/resource abuse | MIME/signature, UTF-8, size/body and Temporal payload limits | No antivirus or complete parser exploitation defense |
| Duplicate/replay ingestion | Duplicate evidence/outbox | Fingerprinted workflow identity, journal locks, stable analysis IDs, transactions | New keys/semantic content intentionally create new work |
| Content tampering | Misleading evidence | Signed hashes checked against live content | Cannot establish truth before acquisition |
| Database manipulation | Changed analyses/lineage | Immutable analysis triggers; signed chain and stored-record comparison | DBA can delete evidence/deny service; key+DB compromise not solved |
| Object tampering | Changed raw/image/archive | Live raw/media hashes; signed metadata; GCM authentication | Deletion is unavailability; no independent backup anchor |
| Signature forgery | Fake provenance | Standard Ed25519 with trusted configured public keys | Key theft/trust-key replacement/rotation need operations controls |
| Nonce misuse | Encryption failure | 96-bit committed counter per key fingerprint; fail closed on lost/exhausted state | Never rewind/copy allocator unsafely; local adapter, no KMS |
| Secret leakage | Credential exposure | Private-volume keys; read-only API mount; allowlisted audit; redacted logs/scans; live traces off | Bounded patterns/fields, not universal DLP |
| Future SSRF | Internal network access | Upload route does not fetch supplied metadata URLs | Operator imports/future connectors need explicit SSRF/network policy |
| Poisoned content | False conclusions | Original bytes; explicit model-output evidence; immutable lineage | No fact checking or adversarial-content detection |
| AI/model errors | Wrong entities/events/sentiment | Typed results; curated candidates; ambiguity abstention; unavailable models explicit | Offline rules uncalibrated; human evaluation review pending |
| Audit-log mutation | Hide actions | Allowlisted persistent SQL; identity hashes; sink failures propagate | Audit is not cryptographically append-only against DBA |
| Resource abuse | API/worker overload | Redis limits, bounded bodies, retries/timeouts | No production HA/load-shedding claim |

## Hashing, encryption, signatures and transport

SHA-256 maps bytes to a deterministic 256-bit digest for change detection. It does not
hide content or identify a signer. AegisNews uses `hashlib` for raw/object and lineage
hashes. Algorithm reference: [NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final).

AES-256-GCM is authenticated encryption using a secret 256-bit key and unique nonce.
It protects stored signed-manifest archives, not normal HTTP response bodies. Algorithm/
key/version metadata and document ID are bound as associated data. Modified ciphertext
raises `InvalidTag`. Reference: [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final).

Ed25519 signs the canonical manifest body, including ordered lineage/hash information.
The private key signs and trusted public key verifies. Changed signed bytes fail.
This establishes origin relative to that key, not factual truth, legal nonrepudiation
or independently trusted time. Reference/test vectors: [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032).

TLS protects traffic between endpoints and is distinct from these stored-data controls.
The loopback demo uses HTTP. Production TLS/identity/key operations are outside this phase.

## Key and nonce lifecycle

`keys-init` generates development AES/Ed25519 keys in a dedicated private Docker volume.
API mounts it read-only; worker writes the shared SQLite nonce allocator. A counter per
AES-key fingerprint commits consumption before encryption, so failures consume nonces.
Nonces are 12 bytes. Missing allocator state and exhaustion fail closed; rotate before
2^32 encryptions per key. Never restore an old counter or copy an AES key without its
allocator. Reset deletes both key and allocator state and generates fresh keys. File/
SQLite storage is a development adapter; KMS and independent trust anchors are deferred.

## Executed security demo

`python scripts/demo.py security` passed 14 controls: auth required, authorized scopes,
viewer ingestion/analyst audit denied, raw hash/live provenance, raw/SQL/image tamper
detection and restoration, AES decryption/ciphertext rejection, Ed25519 verification/
changed-content rejection, persistent audit and log/audit redaction. [Raw report](../evidence/security-demo.json).
No JWT/private key/plaintext secret is exported. Existing security tests cover bad claims,
scope escalation, nonce failures and immutable analysis enforcement.

Changes restore in `finally`. An OS kill/power loss during the optional hold can bypass
cleanup; `demo-reset` recovers isolated synthetic data. Never use this tooling on shared data.

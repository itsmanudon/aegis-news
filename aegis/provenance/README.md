# Provenance boundary

`service.py` signs chains of frozen ProvenanceRecord values with SHA-256 evidence
hashes and Ed25519 manifests. Consumers provide raw, normalization, and artifact
records and inject CryptoProvider plus an optional immutable manifest store.
Verification checks signatures, lineage, and all evidence bytes. See
[security integration](../../docs/security-crypto.md).

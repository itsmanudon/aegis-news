"""How a feed consumer checks a bundle against its signed manifest, offline.

Uses only the standard library and ``cryptography``, so a consumer can copy this module.

What a consumer can check, given a bundle, the manifest it lists and the pinned public key:

- **The signature.** Ed25519 over the canonical JSON of the manifest without its
  ``signature`` field.
- **The chain.** Each chain hash is SHA-256 of ``{"previous": <hash>, "record": <record>}``,
  starting from 64 zeros.
- **The document.** The manifest's ``normalization`` record names the bundle's document.
- **Every analysis in the bundle.** Its record's ``content_hash`` is SHA-256 of the
  analysis's canonical JSON, exactly as the bundle delivers it.

What it cannot check: the normalized document and the raw content are hashed with their
text, which the feed never sends. So the title, URL, source, ``available_at``, entities,
instruments and events are not covered by a hash the consumer can recompute; they rest on
the authenticated transport.
"""

import base64
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

GENESIS = "0" * 64


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class BundleCheck:
    signature_valid: bool
    chain_valid: bool
    document_matches: bool
    analyses_verified: tuple[str, ...] = ()
    analyses_unverified: tuple[str, ...] = field(default=())

    @property
    def valid(self) -> bool:
        return (
            self.signature_valid
            and self.chain_valid
            and self.document_matches
            and not self.analyses_unverified
        )


def verify_bundle(
    item: dict[str, Any], manifest: dict[str, Any], public_key_pem: str
) -> BundleCheck:
    """Check one feed item (parsed JSON) against one manifest (parsed JSON)."""
    key = serialization.load_pem_public_key(public_key_pem.encode())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Ed25519 public key required")
    body = canonical({name: value for name, value in manifest.items() if name != "signature"})
    try:
        key.verify(base64.b64decode(manifest["signature"], validate=True), body)
        signature_valid = True
    except (InvalidSignature, ValueError, KeyError):
        signature_valid = False

    records = manifest.get("records", [])
    previous, chain = GENESIS, []
    for record in records:
        previous = sha256(canonical({"previous": previous, "record": record}))
        chain.append(previous)
    chain_valid = chain == list(manifest.get("chain_hashes", []))

    document_id = item["document"]["document_id"]
    document_matches = any(
        record["operation"] == "normalization" and record["subject_id"] == document_id
        for record in records
    )
    signed = {
        record["subject_id"]: record["content_hash"]
        for record in records
        if record["operation"] == "analysis"
    }
    verified: list[str] = []
    unverified: list[str] = []
    for analysis in item.get("analyses", []):
        identity = analysis["analysis_id"]
        good = signed.get(identity) == sha256(canonical(analysis))
        (verified if good else unverified).append(identity)
    return BundleCheck(
        signature_valid=signature_valid,
        chain_valid=chain_valid,
        document_matches=document_matches,
        analyses_verified=tuple(verified),
        analyses_unverified=tuple(unverified),
    )

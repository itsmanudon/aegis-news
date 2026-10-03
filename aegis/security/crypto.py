"""Standard cryptography with the frozen provider/payload contracts."""

import hashlib
import json
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, ConfigDict

from aegis.security.keys import KeyProvider


class EncryptedPayload(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", ser_json_bytes="base64", val_json_bytes="base64"
    )
    key_id: str
    algorithm: str
    nonce: bytes
    ciphertext: bytes


class Signature(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", ser_json_bytes="base64", val_json_bytes="base64"
    )
    key_id: str
    algorithm: str
    value: bytes


class CryptoProvider(Protocol):
    def hash(self, content: bytes) -> str: ...
    def encrypt(
        self, content: bytes, *, key_id: str, associated_data: bytes
    ) -> EncryptedPayload: ...
    def decrypt(self, payload: EncryptedPayload, *, associated_data: bytes) -> bytes: ...
    def sign(self, content: bytes, *, key_id: str) -> Signature: ...
    def verify(self, content: bytes, signature: Signature) -> bool: ...


class StandardCryptoProvider:
    def __init__(self, keys: KeyProvider) -> None:
        self.keys = keys

    def hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _aes(self, key_id: str) -> AESGCM:
        key = self.keys.encryption_key(key_id)
        if len(key) != 32:
            raise ValueError("AES-256 key required")
        return AESGCM(key)

    @staticmethod
    def _aad(key_id: str, associated_data: bytes) -> bytes:
        header = json.dumps(
            {"algorithm": "AES-256-GCM", "key_id": key_id, "version": 1},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return header + b"\x00" + associated_data

    def encrypt(self, content: bytes, *, key_id: str, associated_data: bytes) -> EncryptedPayload:
        aes = self._aes(key_id)
        nonce = self.keys.next_nonce(key_id)
        if len(nonce) != 12:
            raise ValueError("96-bit nonce required")
        return EncryptedPayload(
            key_id=key_id,
            algorithm="AES-256-GCM",
            nonce=nonce,
            ciphertext=aes.encrypt(nonce, content, self._aad(key_id, associated_data)),
        )

    def decrypt(self, payload: EncryptedPayload, *, associated_data: bytes) -> bytes:
        if payload.algorithm != "AES-256-GCM" or len(payload.nonce) != 12:
            raise ValueError("Unsupported encrypted payload")
        return self._aes(payload.key_id).decrypt(
            payload.nonce, payload.ciphertext, self._aad(payload.key_id, associated_data)
        )

    def sign(self, content: bytes, *, key_id: str) -> Signature:
        return Signature(
            key_id=key_id, algorithm="Ed25519", value=self.keys.signing_key(key_id).sign(content)
        )

    def verify(self, content: bytes, signature: Signature) -> bool:
        if signature.algorithm != "Ed25519":
            return False
        try:
            self.keys.verification_key(signature.key_id).verify(signature.value, content)
            return True
        except (InvalidSignature, ValueError):
            return False

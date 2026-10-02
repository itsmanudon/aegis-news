"""Interfaces only. Implement with PyCA during the security phase, never custom crypto."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class EncryptedPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    key_id: str
    algorithm: str
    nonce: bytes
    ciphertext: bytes


class Signature(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
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

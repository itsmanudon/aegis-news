"""Local development keys. Consumers depend on KeyProvider, not file storage."""

import hashlib
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SigningKey(Protocol):
    def sign(self, data: bytes) -> bytes: ...


class VerificationKey(Protocol):
    def verify(self, signature: bytes, data: bytes) -> None: ...


class KeyProvider(Protocol):
    def encryption_key(self, key_id: str) -> bytes: ...
    def signing_key(self, key_id: str) -> SigningKey: ...
    def verification_key(self, key_id: str) -> VerificationKey: ...
    def next_nonce(self, key_id: str) -> bytes: ...


def validate_key_id(key_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id):
        raise ValueError("Invalid key identifier")


class FileKeyProvider:
    """Never copy AES keys without their nonce database or restore an old counter.

    A transaction commits each counter before encryption. Aborted encryptions consume
    a nonce; multiple threads/processes share the same allocator. Rotate before 2**32
    encryptions. File storage is a development adapter, not a production KMS.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()

    def _read(self, key_id: str, suffix: str) -> bytes:
        validate_key_id(key_id)
        path = self.directory / f"{key_id}.{suffix}"
        try:
            if path.is_symlink():
                raise ValueError("Invalid key file")
            return path.read_bytes()
        except OSError:
            raise ValueError("Key unavailable") from None

    def encryption_key(self, key_id: str) -> bytes:
        key = self._read(key_id, "aes.key")
        if len(key) != 32:
            raise ValueError("AES-256 key required")
        return key

    def signing_key(self, key_id: str) -> Ed25519PrivateKey:
        key = serialization.load_pem_private_key(self._read(key_id, "ed25519.key"), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Ed25519 key required")
        return key

    def verification_key(self, key_id: str) -> Ed25519PublicKey:
        key = serialization.load_pem_public_key(self._read(key_id, "ed25519.pub"))
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("Ed25519 key required")
        return key

    def next_nonce(self, key_id: str) -> bytes:
        fingerprint = hashlib.sha256(self.encryption_key(key_id)).hexdigest()
        path = self.directory / "nonces.sqlite3"
        # mode=rw intentionally refuses to recreate lost allocator state.
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=rw", uri=True, timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT counter FROM nonces WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
            if row is None or row[0] >= 2**32:
                raise ValueError("Nonce state unavailable or exhausted; rotate key")
            counter = int(row[0]) + 1
            db.execute("UPDATE nonces SET counter=? WHERE fingerprint=?", (counter, fingerprint))
        return counter.to_bytes(12, "big")


def generate_development_keys(directory: Path, key_id: str) -> None:
    validate_key_id(key_id)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    paths = [
        directory / f"{key_id}.{suffix}" for suffix in ("aes.key", "ed25519.key", "ed25519.pub")
    ]
    if any(path.exists() for path in paths):
        raise FileExistsError("Key already exists; choose a new key id")
    aes = AESGCM.generate_key(bit_length=256)
    signing = Ed25519PrivateKey.generate()
    values = [
        aes,
        signing.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        signing.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    ]
    for path, value in zip(paths, values, strict=True):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
    with closing(sqlite3.connect(directory / "nonces.sqlite3")) as db, db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS nonces "
            "(fingerprint TEXT PRIMARY KEY, counter INTEGER NOT NULL)"
        )
        db.execute("INSERT INTO nonces VALUES (?, 0)", (hashlib.sha256(aes).hexdigest(),))

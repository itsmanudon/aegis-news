import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from cryptography.exceptions import InvalidTag

from aegis.security.crypto import EncryptedPayload, Signature, StandardCryptoProvider
from aegis.security.keys import FileKeyProvider, generate_development_keys


@pytest.fixture
def keys(tmp_path):
    generate_development_keys(tmp_path / "keys", "dev")
    return FileKeyProvider(tmp_path / "keys")


def test_hash_and_authenticated_encryption(keys):
    crypto = StandardCryptoProvider(keys)
    assert crypto.hash(b"abc") == hashlib.sha256(b"abc").hexdigest()
    encrypted = crypto.encrypt(b"synthetic secret", key_id="dev", associated_data=b"doc:1")
    assert len(encrypted.nonce) == 12
    assert len(encrypted.ciphertext) == len(b"synthetic secret") + 16
    assert crypto.decrypt(encrypted, associated_data=b"doc:1") == b"synthetic secret"
    assert EncryptedPayload.model_validate_json(encrypted.model_dump_json()) == encrypted
    for payload, aad in [
        (encrypted, b"doc:2"),
        (
            encrypted.model_copy(
                update={
                    "ciphertext": encrypted.ciphertext[:-1] + bytes([encrypted.ciphertext[-1] ^ 1])
                }
            ),
            b"doc:1",
        ),
        (encrypted.model_copy(update={"nonce": b"0" * 12}), b"doc:1"),
    ]:
        with pytest.raises(InvalidTag):
            crypto.decrypt(payload, associated_data=aad)


def test_nonce_allocation_survives_restart_and_concurrency(keys):
    def encrypt(_):
        return (
            StandardCryptoProvider(FileKeyProvider(keys.directory))
            .encrypt(b"x", key_id="dev", associated_data=b"")
            .nonce
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        nonces = list(pool.map(encrypt, range(100)))
    assert len(set(nonces)) == 100


def test_nonce_allocator_fails_closed_if_lost_or_exhausted(keys):
    fingerprint = hashlib.sha256(keys.encryption_key("dev")).hexdigest()
    with closing(sqlite3.connect(keys.directory / "nonces.sqlite3")) as db, db:
        db.execute("UPDATE nonces SET counter=? WHERE fingerprint=?", (2**32, fingerprint))
    with pytest.raises(ValueError):
        StandardCryptoProvider(keys).encrypt(b"x", key_id="dev", associated_data=b"")
    (keys.directory / "nonces.sqlite3").unlink()
    with pytest.raises(sqlite3.OperationalError):
        StandardCryptoProvider(keys).encrypt(b"x", key_id="dev", associated_data=b"")


def test_envelope_key_id_is_authenticated(keys):
    crypto = StandardCryptoProvider(keys)
    encrypted = crypto.encrypt(b"x", key_id="dev", associated_data=b"context")
    (keys.directory / "alias.aes.key").write_bytes(keys.encryption_key("dev"))
    with pytest.raises(InvalidTag):
        crypto.decrypt(encrypted.model_copy(update={"key_id": "alias"}), associated_data=b"context")


def test_ed25519_and_key_loading(keys):
    crypto = StandardCryptoProvider(keys)
    signature = crypto.sign(b"manifest", key_id="dev")
    assert Signature.model_validate_json(signature.model_dump_json()) == signature
    assert crypto.verify(b"manifest", signature)
    assert not crypto.verify(b"changed", signature)
    assert not crypto.verify(b"manifest", signature.model_copy(update={"value": b"x" * 64}))
    with pytest.raises(ValueError):
        keys.encryption_key("../dev")
    with pytest.raises(ValueError):
        keys.encryption_key("missing")
    with pytest.raises(FileExistsError):
        generate_development_keys(keys.directory, "dev")
    (keys.directory / "bad.aes.key").write_bytes(b"short")
    with pytest.raises(ValueError):
        keys.encryption_key("bad")

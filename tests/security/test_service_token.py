from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

from aegis.security.auth import TokenValidator
from aegis.security.keys import generate_signing_keys
from aegis.security.service_token import mint_service_token
from aegis.settings import Settings
from scripts import service_token as cli

ISSUER, AUDIENCE = "https://owner.test/aegis", "aegisnews"


def settings(**changes):
    return Settings(
        security_enabled=True,
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_algorithms=["EdDSA"],
        **changes,
    )


def mint(key, **changes):
    arguments = dict(
        key_id="stockviz-test",
        issuer=ISSUER,
        audience=AUDIENCE,
        client_id="stockviz-sync",
        scopes=["feed:read"],
        lifetime=timedelta(minutes=15),
        maximum_lifetime=timedelta(days=1),
    )
    arguments.update(changes)
    return mint_service_token(key, **arguments)


def test_minted_token_is_accepted_as_a_scoped_service_principal():
    key = Ed25519PrivateKey.generate()
    validator = TokenValidator(settings(), public_keys={"stockviz-test": key.public_key()})
    principal = validator.validate(mint(key, scopes=["feed:read", "feed:read"]))
    assert (principal.kind, principal.client_id, principal.subject) == (
        "service",
        "stockviz-sync",
        "stockviz-sync",
    )
    assert principal.scopes == {"feed:read"}
    assert principal.permits("feed:read")
    assert not principal.permits("documents:read")
    assert not principal.permits("ingestions:write")


def test_minted_token_is_rejected_by_every_wrong_verifier():
    key = Ed25519PrivateKey.generate()
    token = mint(key)
    trusted = {"stockviz-test": key.public_key()}
    other_key = {"stockviz-test": Ed25519PrivateKey.generate().public_key()}
    for validator in (
        TokenValidator(settings(), public_keys=other_key),
        TokenValidator(settings(), public_keys={"another-id": key.public_key()}),
        TokenValidator(settings(oidc_max_token_lifetime=60), public_keys=trusted),
        TokenValidator(settings().model_copy(update={"oidc_audience": "x"}), public_keys=trusted),
        TokenValidator(settings().model_copy(update={"oidc_issuer": "x"}), public_keys=trusted),
    ):
        with pytest.raises(ValueError, match="Invalid access token"):
            validator.validate(token)
    expired = mint(key, now=datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(ValueError, match="Invalid access token"):
        TokenValidator(settings(), public_keys=trusted).validate(expired)


@pytest.mark.parametrize(
    "changes",
    [
        dict(scopes=[]),
        dict(scopes=["feed:read", "feed:write"]),
        dict(scopes=["*"]),
        dict(client_id=""),
        dict(client_id="x" * 257),
        dict(issuer=""),
        dict(audience=""),
        dict(key_id="../escape"),
        dict(lifetime=timedelta(0)),
        dict(lifetime=timedelta(days=1, seconds=1)),
    ],
)
def test_mint_refuses_what_the_api_would_refuse(changes):
    with pytest.raises(ValueError):
        mint(Ed25519PrivateKey.generate(), **changes)


def test_generate_writes_private_files_and_never_overwrites(tmp_path):
    private, public = generate_signing_keys(tmp_path / "keys", "stockviz-test")
    assert private.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "keys").stat().st_mode & 0o777 == 0o700
    assert b"PRIVATE KEY" in private.read_bytes()
    assert b"PUBLIC KEY" in public.read_bytes() and b"PRIVATE" not in public.read_bytes()
    with pytest.raises(FileExistsError):
        generate_signing_keys(tmp_path / "keys", "stockviz-test")
    with pytest.raises(ValueError):
        generate_signing_keys(tmp_path / "keys", "bad id")


def test_cli_generates_a_key_then_mints_a_token_the_api_accepts(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no .env here, so defaults apply
    assert cli.main(["generate", "--key-id", "stockviz-test", "--directory", str(tmp_path)]) == 0
    printed = capsys.readouterr().out
    assert "AEGIS_OIDC_PUBLIC_KEYS=" in printed and "PRIVATE KEY" not in printed
    key_file = tmp_path / "stockviz-test.ed25519.key"
    mint_arguments = [
        "mint",
        "--key-file",
        str(key_file),
        "--key-id",
        "stockviz-test",
        "--issuer",
        ISSUER,
        "--audience",
        AUDIENCE,
        "--client-id",
        "stockviz-sync",
        "--scope",
        "feed:read",
    ]
    assert cli.main(mint_arguments) == 0
    output = capsys.readouterr()
    token = output.out.strip()
    assert "\n" not in token and output.err == ""
    public = serialization.load_pem_public_key(
        (tmp_path / "stockviz-test.ed25519.pub").read_bytes()
    )
    principal = TokenValidator(settings(), public_keys={"stockviz-test": public}).validate(token)
    assert principal.scopes == {"feed:read"}
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 15 * 60

    # Failures say what is wrong and print neither a token nor key material.
    assert cli.main([*mint_arguments, "--minutes", "100000"]) == 1
    assert cli.main([*mint_arguments, "--scope", "admin:everything"]) == 1
    missing = [a if a != str(key_file) else str(tmp_path / "absent.key") for a in mint_arguments]
    assert cli.main(missing) == 1
    rsa = tmp_path / "rsa.key"
    rsa.write_bytes(
        generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    wrong_type = [a if a != str(key_file) else str(rsa) for a in mint_arguments]
    assert cli.main(wrong_type) == 1
    failures = capsys.readouterr()
    assert failures.out == "" and "PRIVATE KEY" not in failures.err
    assert failures.err.count("service_token:") == 4

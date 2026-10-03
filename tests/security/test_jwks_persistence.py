import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from aegis.security.audit import AuditLog
from aegis.security.auth import TokenValidator
from aegis.security.persistence import (
    AuditEventRow,
    SignedManifestRow,
    SQLAuditSink,
    SQLManifestStore,
)
from aegis.settings import Settings


def test_jwks_rotation_and_token_types():
    keys = [Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()]
    document = {"keys": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(document).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    settings = Settings(
        security_enabled=True,
        oidc_issuer="https://issuer.test",
        oidc_audience="aegis",
        oidc_algorithms=["EdDSA"],
        oidc_jwks_url=f"http://127.0.0.1:{server.server_port}/jwks",
    )
    validator = TokenValidator(settings)

    def token(index, **headers):
        now = datetime.now(UTC)
        return jwt.encode(
            dict(
                iss=settings.oidc_issuer,
                aud="aegis",
                sub="synthetic",
                iat=now,
                exp=now + timedelta(minutes=5),
                roles=["viewer"],
                scope="documents:read",
            ),
            keys[index],
            algorithm="EdDSA",
            headers={"kid": str(index), "typ": "at+jwt", **headers},
        )

    try:
        for index in range(2):
            jwk = json.loads(jwt.algorithms.OKPAlgorithm.to_jwk(keys[index].public_key()))
            document["keys"] = [{**jwk, "kid": str(index), "alg": "EdDSA", "use": "sig"}]
            if index:
                validator.jwks.get_signing_keys(refresh=True)
            assert validator.validate(token(index)).permits("documents:read")
        with pytest.raises(ValueError):
            validator.validate(token(1, typ="JWT"))
        with pytest.raises(ValueError):
            validator.validate(token(1, kid="unknown"))
        with pytest.raises(ValueError):
            validator.validate(token(0, kid="1"))
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def test_security_persistence_roundtrip():
    engine = create_engine("sqlite://")
    for table in (AuditEventRow.__table__, SignedManifestRow.__table__):
        table.create(engine)
    try:
        sink = SQLAuditSink(engine)
        AuditLog(sink).emit("security_change", actor="synthetic", outcome="success")
        assert sink.recent(10)[0].action == "security_change"
        assert sink.recent(10)[0].actor_hash != "synthetic"
        store = SQLManifestStore(engine)
        store.append("a" * 64, {"synthetic": True}, "dev", datetime.now(UTC))
        with pytest.raises(IntegrityError):
            store.append("a" * 64, {"synthetic": False}, "dev", datetime.now(UTC))
    finally:
        engine.dispose()

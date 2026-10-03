import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from aegis.contracts.api import CollectionResponse, CursorPagination, ResponseMeta, SingleResponse
from aegis.provenance.service import SignedManifest, VerificationResult
from aegis.security.audit import AuditEvent
from aegis.security.auth import Principal, authenticate, require_scopes

router = APIRouter(prefix="/security", tags=["security"])


class IdentityResponse(BaseModel):
    subject: str
    kind: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest: SignedManifest
    contents: dict[str, str] = Field(max_length=100)  # Base64, bounded by middleware.


@router.get("/me", response_model=SingleResponse[IdentityResponse])
def me(
    request: Request, principal: Annotated[Principal, Depends(authenticate)]
) -> SingleResponse[IdentityResponse]:
    return SingleResponse(
        data=IdentityResponse(
            subject=principal.subject,
            kind=principal.kind,
            roles=tuple(sorted(principal.roles)),
            scopes=tuple(sorted(s for s in principal.scopes if principal.permits(s))),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/verify",
    response_model=SingleResponse[VerificationResult],
    dependencies=[require_scopes("security:verify")],
)
def verify(body: VerificationRequest, request: Request) -> SingleResponse[VerificationResult]:
    try:
        contents = {
            key: base64.b64decode(value, validate=True) for key, value in body.contents.items()
        }
    except ValueError:
        raise HTTPException(422) from None
    result: VerificationResult = request.app.state.provenance.verify(body.manifest, contents)
    audit = request.app.state.audit
    for action, valid in [
        ("integrity_verification", result.valid),
        ("signature_verification", result.signature_valid),
    ]:
        audit.emit(
            action,
            actor=request.state.principal.issuer + ":" + request.state.principal.subject,
            request_id=request.state.request_id,
            outcome="success" if valid else "failure",
        )
    return SingleResponse(data=result, meta=ResponseMeta(request_id=request.state.request_id))


@router.get(
    "/audit",
    response_model=CollectionResponse[AuditEvent],
    dependencies=[require_scopes("audit:read")],
)
def audit_events(
    request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> CollectionResponse[AuditEvent]:
    return CollectionResponse(
        data=request.app.state.audit.sink.recent(limit),
        pagination=CursorPagination(),
        meta=ResponseMeta(request_id=request.state.request_id),
    )

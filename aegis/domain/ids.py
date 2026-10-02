"""Central ID policy: prefixed UUID4 today; wire identifiers stay opaque."""

from typing import Annotated, Literal
from uuid import uuid4

from pydantic import StringConstraints

IdPrefix = Literal[
    "src", "ing", "raw", "media", "doc", "ent", "mention", "map", "ana", "evt", "prov", "msg"
]


def new_id(prefix: IdPrefix) -> str:
    return f"{prefix}_{uuid4()}"


def id_constraint(prefix: str) -> StringConstraints:
    return StringConstraints(
        pattern=rf"^{prefix}_[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$"
    )


SourceId = Annotated[str, id_constraint("src")]
IngestionId = Annotated[str, id_constraint("ing")]
RawObjectId = Annotated[str, id_constraint("raw")]
MediaId = Annotated[str, id_constraint("media")]
DocumentId = Annotated[str, id_constraint("doc")]
EntityId = Annotated[str, id_constraint("ent")]
MentionId = Annotated[str, id_constraint("mention")]
MappingId = Annotated[str, id_constraint("map")]
AnalysisId = Annotated[str, id_constraint("ana")]
NewsEventId = Annotated[str, id_constraint("evt")]
ProvenanceId = Annotated[str, id_constraint("prov")]
MessageId = Annotated[str, id_constraint("msg")]

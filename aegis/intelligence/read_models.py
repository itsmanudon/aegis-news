"""Bounded PostgreSQL projections with explicit temporal and model selection policies."""

import base64
import binascii
import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.orm import Session

from aegis.contracts.intelligence import (
    AnalyticsReport,
    DocumentDiscoveryItem,
    ModelIdentity,
    TopicMembership,
    TopicSummary,
)
from aegis.domain.models import NewsDocument, NonEmpty, Source

TopicIdentity = tuple[str, str, str, str, str]
TOPIC_POLICY = (
    "Latest available topic analysis per document and exact provider/model/version/configuration; "
    "availability then analysis ID descending. Exact labels; unique documents; "
    "maximum matching confidence."
)
SENTIMENT_POLICY = (
    "Unique documents; latest available document-level sentiment analysis per document "
    "across models, "
    "availability then analysis ID descending; first document-level output in stored order. "
    "Entity-specific outputs excluded."
)


def pack(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def unpack(value: str, maximum: int) -> Any:
    if not value or len(value) > maximum or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("invalid opaque value")
    try:
        result = json.loads(
            base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        )
        if pack(result) != value:
            raise ValueError("noncanonical opaque value")
        return result
    except (ValueError, UnicodeDecodeError, binascii.Error, RecursionError) as exc:
        raise ValueError("invalid opaque value") from exc


def topic_id(identity: TopicIdentity) -> str:
    return "topic_v1_" + pack(list(identity))


def parse_topic_id(value: str) -> TopicIdentity:
    if not value.startswith("topic_v1_"):
        raise ValueError("invalid topic identity")
    values = unpack(value[9:], 32768)
    if (
        not isinstance(values, list)
        or len(values) != 5
        or any(not isinstance(v, str) for v in values)
    ):
        raise ValueError("invalid topic identity")
    if any("\u0000" in value for value in values):
        # PostgreSQL text cannot contain NUL; reject before passing opaque client input to SQL.
        raise ValueError("invalid topic identity")
    TypeAdapter(NonEmpty).validate_python(values[0])
    ModelIdentity(
        provider=values[1],
        model_name=values[2],
        model_version=values[3],
        configuration_hash=values[4],
    )
    return cast(TopicIdentity, tuple(values))


def fingerprint(filters: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(filters, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def encode_cursor(cutoff: datetime, filters: dict[str, Any], key: list[Any]) -> str:
    return pack(
        {
            "v": 1,
            "as_of": cutoff.astimezone(UTC).isoformat(),
            "filters": fingerprint(filters),
            "key": key,
        }
    )


def decode_cursor(
    value: str, filters: dict[str, Any], cutoff: datetime | None
) -> tuple[datetime, list[Any]]:
    data = unpack(value, 32768)
    if not isinstance(data, dict) or set(data) != {"v", "as_of", "filters", "key"}:
        raise ValueError("invalid cursor")
    if (
        type(data["v"]) is not int
        or data["v"] != 1
        or data["filters"] != fingerprint(filters)
        or not isinstance(data["key"], list)
    ):
        raise ValueError("cursor filter mismatch")
    try:
        snapshot = datetime.fromisoformat(data["as_of"])
        if snapshot.tzinfo is None or (cutoff is not None and snapshot != cutoff):
            raise ValueError("cursor cutoff mismatch")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid cursor cutoff") from exc
    return snapshot.astimezone(UTC), data["key"]


TOPIC_CTE = """latest_topics AS (
  SELECT DISTINCT ON (a.document_id, a.provider, a.model_name,
    a.model_version, a.configuration_hash) a.*
  FROM analyses a JOIN documents d ON d.document_id=a.document_id
  WHERE a.analysis_type='topic' AND a.available_at<=:cutoff AND d.created_at<=:cutoff
    {identity_filter}
  ORDER BY a.document_id, a.provider, a.model_name, a.model_version, a.configuration_hash,
    a.available_at DESC, a.analysis_id DESC
), topic_members AS (
  SELECT a.document_id, a.analysis_id, a.provider, a.model_name, a.model_version,
    a.configuration_hash, a.available_at, o->>'label' AS label,
    MAX((o->>'confidence')::double precision) AS confidence
  FROM latest_topics a CROSS JOIN LATERAL jsonb_array_elements(a.outputs) o
  WHERE o->>'result_type'='topic' {label_filter}
  GROUP BY a.document_id, a.analysis_id, a.provider, a.model_name, a.model_version,
    a.configuration_hash, a.available_at, o->>'label'
)"""


def topic_cte(identity: TopicIdentity | None, params: dict[str, Any]) -> str:
    if identity is None:
        return TOPIC_CTE.format(identity_filter="", label_filter="")
    label, provider, model_name, model_version, configuration_hash = identity
    params.update(
        label=label,
        provider=provider,
        model_name=model_name,
        model_version=model_version,
        configuration_hash=configuration_hash,
    )
    return TOPIC_CTE.format(
        identity_filter=(
            "AND a.provider=:provider AND a.model_name=:model_name "
            "AND a.model_version=:model_version AND a.configuration_hash=:configuration_hash"
        ),
        label_filter="AND o->>'label'=:label",
    )


def rows(session: Session, sql: str, params: dict[str, Any]) -> list[Any]:
    # This transaction owns its timeout; expensive reads never run without a server-side bound.
    session.execute(text("SET LOCAL statement_timeout = '5000ms'"))
    return list(session.execute(text(sql), params).mappings())


def model(row: Any) -> ModelIdentity:
    return ModelIdentity(**{key: row[key] for key in ModelIdentity.model_fields})


def topic_summary(row: Any, cutoff: datetime) -> TopicSummary:
    identity = cast(
        TopicIdentity,
        tuple(
            row[key]
            for key in ("label", "provider", "model_name", "model_version", "configuration_hash")
        ),
    )
    return TopicSummary(
        topic_id=topic_id(identity),
        label=row["label"],
        model=model(row),
        document_count=row["document_count"],
        first_available_at=row["first_available_at"],
        latest_available_at=row["latest_available_at"],
        as_of=cutoff,
        selection_policy=TOPIC_POLICY,
    )


def topics(
    session: Session,
    cutoff: datetime,
    limit: int,
    query: str,
    after: list[Any] | None = None,
    identity: TopicIdentity | None = None,
) -> list[TopicSummary]:
    params: dict[str, Any] = {
        "cutoff": cutoff,
        "limit": limit + 1,
        "q": "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",
    }
    cte = topic_cte(identity, params)
    clause = ""
    if after:
        params.update(
            dict(
                zip(
                    (
                        "last_label",
                        "last_provider",
                        "last_model_name",
                        "last_model_version",
                        "last_configuration_hash",
                    ),
                    after,
                    strict=True,
                )
            )
        )
        clause = (
            "AND (label,provider,model_name,model_version,configuration_hash) > "
            "(:last_label,:last_provider,:last_model_name,:last_model_version,"
            ":last_configuration_hash)"
        )
    sql = (
        "WITH "
        + cte
        + """, summaries AS (
      SELECT label,provider,model_name,model_version,configuration_hash,
        COUNT(DISTINCT document_id) AS document_count,
        MIN(available_at) AS first_available_at, MAX(available_at) AS latest_available_at
      FROM topic_members GROUP BY label,provider,model_name,model_version,configuration_hash
    ) SELECT * FROM summaries WHERE label ILIKE :q ESCAPE '\\' """
        + clause
        + """
    ORDER BY label,provider,model_name,model_version,configuration_hash LIMIT :limit"""
    )
    return [topic_summary(row, cutoff) for row in rows(session, sql, params)]


def population(
    cutoff: datetime,
    source_id: str | None,
    query: str,
    identity: TopicIdentity | None,
    start: datetime | None,
    end: datetime | None,
    time_basis: str,
) -> tuple[str, dict[str, Any]]:
    if time_basis not in ("published_at", "first_seen_at"):
        raise ValueError("invalid time basis")
    params: dict[str, Any] = {
        "cutoff": cutoff,
        "source_id": source_id,
        "q": "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",
        "start": start,
        "end": end,
    }
    topic_sql = topic_cte(identity, params) + "," if identity else ""
    topic_filter = (
        "AND d.document_id IN (SELECT document_id FROM topic_members)" if identity else ""
    )
    time_filter = f"WHERE {time_basis}>=:start AND {time_basis}<:end" if start else ""
    return (
        topic_sql
        + f"""
    eligible_docs AS (
      SELECT d.* FROM documents d WHERE d.created_at<=:cutoff
        AND (CAST(:source_id AS text) IS NULL OR d.source_id=:source_id)
        AND (d.title ILIKE :q ESCAPE '\\' OR d.text ILIKE :q ESCAPE '\\') {topic_filter}
    ), population AS (SELECT * FROM eligible_docs {time_filter})""",
        params,
    )


def chronological(
    session: Session,
    cutoff: datetime,
    limit: int,
    order: str,
    after: list[Any] | None = None,
    source_id: str | None = None,
    query: str = "",
    identity: TopicIdentity | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    time_basis: str = "published_at",
) -> list[DocumentDiscoveryItem]:
    if order not in ("published_at", "first_seen_at"):
        raise ValueError("invalid chronological order")
    cte, params = population(cutoff, source_id, query, identity, start, end, time_basis)
    params["limit"] = limit + 1
    clause = ""
    if after:
        params.update(last_time=after[0], last_id=after[1])
        if after[0] is None:
            clause = f"WHERE d.{order} IS NULL AND d.document_id>:last_id"
        else:
            clause = (
                f"WHERE (d.{order}<:last_time OR (d.{order}=:last_time "
                f"AND d.document_id>:last_id) OR d.{order} IS NULL)"
            )
    assessment_columns = (
        ",t.analysis_id,t.available_at,t.confidence,t.provider,t.model_name,t.model_version,t.configuration_hash"
        if identity
        else ""
    )
    assessment_join = "JOIN topic_members t ON t.document_id=d.document_id" if identity else ""
    sql = (
        "WITH "
        + cte
        + f"""
    SELECT to_jsonb(d) AS document,to_jsonb(s) AS source {assessment_columns}
    FROM population d JOIN sources s ON s.source_id=d.source_id {assessment_join} {clause}
    ORDER BY d.{order} DESC NULLS LAST,d.document_id ASC LIMIT :limit"""
    )
    result: list[DocumentDiscoveryItem] = []
    for row in rows(session, sql, params):
        document = NewsDocument.model_validate(row["document"])
        source = Source.model_validate(row["source"])
        if identity:
            result.append(
                TopicMembership(
                    document=document,
                    source=source,
                    analysis_id=row["analysis_id"],
                    available_at=row["available_at"],
                    confidence=row["confidence"],
                    model=model(row),
                )
            )
        else:
            result.append(DocumentDiscoveryItem(document=document, source=source))
    return result


def analytics(
    session: Session,
    cutoff: datetime,
    start: datetime,
    end: datetime,
    time_basis: str,
    source_id: str | None,
    identity: TopicIdentity | None,
) -> AnalyticsReport:
    cte, params = population(cutoff, source_id, "", identity, start, end, time_basis)
    sql = (
        "WITH "
        + cte
        + f""",
    sentiments AS (
      SELECT DISTINCT ON (a.document_id) a.document_id,a.provider,a.model_name,a.model_version,
        o.value->>'label' AS label
      FROM analyses a JOIN population p ON p.document_id=a.document_id
      CROSS JOIN LATERAL jsonb_array_elements(a.outputs) WITH ORDINALITY AS o(value,position)
      WHERE a.analysis_type='sentiment' AND a.available_at<=:cutoff
        AND o.value->>'result_type'='sentiment' AND o.value->>'entity_id' IS NULL
        AND o.value->>'label' IN ('positive','neutral','negative','mixed')
      ORDER BY a.document_id,a.available_at DESC,a.analysis_id DESC,o.position
    ), classified AS (
      SELECT p.*,s.label,s.provider,s.model_name,s.model_version
      FROM population p LEFT JOIN sentiments s ON s.document_id=p.document_id
    ), coverage AS (
      SELECT ({time_basis} AT TIME ZONE 'UTC')::date AS day, COUNT(*) AS document_count,
        COUNT(label) AS classified_count FROM classified GROUP BY day
    ), source_counts AS (
      SELECT p.source_id,s.name,COUNT(*) AS document_count
      FROM population p JOIN sources s ON s.source_id=p.source_id GROUP BY p.source_id,s.name
    ), model_counts AS (
      SELECT provider,model_name,model_version,COUNT(*) AS document_count FROM sentiments
      GROUP BY provider,model_name,model_version
    ), source_top AS (
      SELECT * FROM source_counts ORDER BY document_count DESC,source_id LIMIT 100
    ), model_top AS (
      SELECT * FROM model_counts
      ORDER BY document_count DESC,provider,model_name,model_version LIMIT 100
    ) SELECT jsonb_build_object(
      'population_count',(SELECT COUNT(*) FROM population),
      'classified_count',(SELECT COUNT(*) FROM sentiments),
      'no_assessment_count',(SELECT COUNT(*) FROM classified WHERE label IS NULL),
      'unknown_time_count',(SELECT COUNT(*) FROM eligible_docs WHERE {time_basis} IS NULL),
      'coverage',COALESCE((SELECT jsonb_agg(to_jsonb(c) ORDER BY day) FROM coverage c),'[]'::jsonb),
      'sources',COALESCE((SELECT jsonb_agg(to_jsonb(s)
        ORDER BY document_count DESC,source_id) FROM source_top s),'[]'::jsonb),
      'sources_other_count',(SELECT COUNT(*) FROM population)
        -COALESCE((SELECT SUM(document_count) FROM source_top),0),
      'models',COALESCE((SELECT jsonb_agg(to_jsonb(m)
        ORDER BY document_count DESC,provider,model_name,model_version)
        FROM model_top m),'[]'::jsonb),
      'models_other_count',(SELECT COUNT(*) FROM sentiments)
        -COALESCE((SELECT SUM(document_count) FROM model_top),0),
      'sentiment',(SELECT jsonb_agg(jsonb_build_object('label',l.label,'document_count',
          (SELECT COUNT(*) FROM sentiments s WHERE s.label=l.label)) ORDER BY l.position)
        FROM (VALUES ('positive',1),('neutral',2),('negative',3),('mixed',4)) AS l(label,position))
    ) AS report"""
    )
    value = rows(session, sql, params)[0]["report"]
    return AnalyticsReport(
        **value,
        start=start,
        end=end,
        as_of=cutoff,
        time_basis=time_basis,
        source_id=source_id,
        topic_id=topic_id(identity) if identity else None,
        selection_policy=SENTIMENT_POLICY,
        limitations=(
            "UTC half-open time window; unique available documents. "
            "Unknown publisher dates are counted outside the window denominator.",
            "Missing persisted assessments cannot distinguish unrun, unavailable, "
            "unsupported-language or abstained inference.",
            "Sentiment confidence is not calibrated public opinion. Configuration hashes "
            "include document context and are not shared model identities.",
            "Source/document registries and timeless associations are mutable; past metadata "
            "edits cannot be reconstructed. Topic labels are exact model assessments.",
            "Only observed UTC days are returned; no historical predictions or "
            "event-occurrence substitution.",
        ),
    )

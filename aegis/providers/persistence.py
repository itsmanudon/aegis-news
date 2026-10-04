"""Acquisition staging/evidence only. Canonical documents are written by Temporal."""

import base64
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, delete, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from aegis.ingestion.inputs import IngestionRequest
from aegis.persistence.models import Base, DocumentRow, SourceRow
from aegis.providers.models import (
    ArticleEvidence,
    ExternalNewsRecord,
    ProviderArticleView,
    ProviderRun,
    YouTubeReference,
    hash_value,
)

Json = JSON().with_variant(JSONB(), "postgresql")


class ProviderArticleRow(Base):
    __tablename__ = "provider_articles"
    article_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.source_id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.document_id"), index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(128), index=True)
    request: Mapped[dict[str, Any]] = mapped_column(Json)
    title: Mapped[str] = mapped_column(String(512))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ArticleAliasRow(Base):
    __tablename__ = "provider_article_aliases"
    alias_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("provider_articles.article_id"), index=True)


class ProviderEvidenceRow(Base):
    __tablename__ = "provider_evidence"
    evidence_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("provider_articles.article_id"), index=True)
    provider: Mapped[str] = mapped_column(String(16))
    metadata_value: Mapped[dict[str, Any]] = mapped_column(Json)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProviderRunRow(Base):
    __tablename__ = "provider_runs"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report: Mapped[dict[str, Any]] = mapped_column(Json)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class YouTubeReferenceRow(Base):
    __tablename__ = "youtube_references"
    video_id: Mapped[str] = mapped_column(String(11), primary_key=True)
    metadata_value: Mapped[dict[str, Any]] = mapped_column(Json)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ProviderStore:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def known(self, record: ExternalNewsRecord) -> ProviderArticleRow | None:
        with self.sessions() as session:
            ids = set(
                session.scalars(
                    select(ArticleAliasRow.article_id).where(
                        ArticleAliasRow.alias_key.in_(record.aliases())
                    )
                )
            )
            if len(ids) > 1:
                raise ValueError("conflicting_acquisition_identities")
            return session.get(ProviderArticleRow, next(iter(ids))) if ids else None

    def publisher(self, name: str, url: str | None) -> str | None:
        with self.sessions() as session:
            query = select(SourceRow).where(SourceRow.name == name).order_by(SourceRow.created_at)
            row = next(
                (
                    r
                    for r in session.scalars(query)
                    if not url or urlsplit(r.url or "").hostname == urlsplit(url).hostname
                ),
                None,
            )
            return row.source_id if row else None

    def prepare(
        self, record: ExternalNewsRecord, source_id: str
    ) -> tuple[ProviderArticleRow, bool]:
        aliases = record.aliases()
        with self.sessions.begin() as session:
            ids = set(
                session.scalars(
                    select(ArticleAliasRow.article_id).where(ArticleAliasRow.alias_key.in_(aliases))
                )
            )
            if len(ids) > 1:
                raise ValueError("conflicting_acquisition_identities")
            row = session.get(ProviderArticleRow, next(iter(ids))) if ids else None
            duplicate = row is not None
            now = datetime.now(UTC)
            if row is None:
                article = record.article()
                request = IngestionRequest(
                    source_id=source_id,
                    idempotency_key="live:" + record.provider + ":" + hash_value(aliases[0]),
                    content_type="application/json",
                    content_base64=base64.b64encode(article.model_dump_json().encode()).decode(),
                    source_url=record.article_url,
                    correlation_id="live-" + record.provider,
                )
                row = ProviderArticleRow(
                    article_id=str(uuid4()),
                    source_id=source_id,
                    document_id=None,
                    workflow_id=None,
                    request=request.model_dump(mode="json"),
                    title=article.title,
                    published_at=article.published_at,
                    acquired_at=now,
                )
                session.add(row)
                session.flush()
            for alias in aliases:
                if session.get(ArticleAliasRow, alias) is None:
                    session.add(ArticleAliasRow(alias_key=alias, article_id=row.article_id))
            evidence_key = (
                record.provider
                + ":"
                + hash_value(record.provider_item_id or record.article_url or record.title)
            )
            if session.get(ProviderEvidenceRow, evidence_key) is None:
                evidence = ArticleEvidence(
                    provider=record.provider,
                    provider_item_id=record.provider_item_id,
                    publisher_name=record.publisher_name,
                    article_url=record.article_url,
                    author=record.author,
                    image_url=record.image_url
                    if record.image_url and record.image_url.startswith("https://")
                    else None,
                    video_url=record.video_url
                    if record.video_url and record.video_url.startswith("https://")
                    else None,
                    acquired_at=now,
                    content_kind="provider excerpt"
                    if record.description or record.body
                    else "headline only",
                )
                # Dataset categories stay acquisition metadata, never AI labels.
                metadata = evidence.model_dump(mode="json")
                metadata["provider_category"] = list(record.provider_category)
                metadata["discovered_at"] = (
                    record.discovered_at.isoformat() if record.discovered_at else None
                )
                session.add(
                    ProviderEvidenceRow(
                        evidence_key=evidence_key,
                        article_id=row.article_id,
                        provider=record.provider,
                        metadata_value=metadata,
                        acquired_at=now,
                    )
                )
            session.flush()
            return row, duplicate

    def submitted(self, article_id: str, workflow_id: str) -> None:
        with self.sessions.begin() as session:
            row = session.get(ProviderArticleRow, article_id)
            assert row is not None
            row.workflow_id = workflow_id

    def completed(self, workflow_id: str, document_id: str) -> None:
        with self.sessions.begin() as session:
            row = session.scalar(
                select(ProviderArticleRow).where(ProviderArticleRow.workflow_id == workflow_id)
            )
            if row:
                row.document_id = document_id

    def run(self, report: ProviderRun) -> None:
        with self.sessions.begin() as session:
            session.merge(
                ProviderRunRow(
                    run_id=report.run_id,
                    report=report.model_dump(mode="json"),
                    created_at=report.created_at,
                )
            )

    def get_run(self, run_id: str) -> ProviderRun | None:
        with self.sessions() as session:
            row = session.get(ProviderRunRow, run_id)
            return ProviderRun.model_validate(row.report) if row else None

    def interrupt_runs(self) -> None:
        with self.sessions.begin() as session:
            for row in session.scalars(
                select(ProviderRunRow).where(
                    ProviderRunRow.report["status"].as_string() == "running"
                )
            ):
                if row.report["status"] == "running":
                    row.report = {**row.report, "status": "interrupted"}

    def videos(self, values: list[YouTubeReference]) -> None:
        with self.sessions.begin() as session:
            for value in values:
                session.merge(
                    YouTubeReferenceRow(
                        video_id=value.video_id,
                        metadata_value=value.model_dump(mode="json"),
                        last_refreshed_at=value.last_refreshed_at,
                        expires_at=value.expires_at,
                    )
                )

    def refresh_videos(self, requested: list[str], values: list[YouTubeReference]) -> None:
        returned = {v.video_id for v in values}
        with self.sessions.begin() as session:
            session.execute(
                delete(YouTubeReferenceRow).where(
                    YouTubeReferenceRow.video_id.in_([i for i in requested if i not in returned])
                )
            )
        self.videos(values)

    def prune(self, now: datetime | None = None) -> int:
        with self.sessions.begin() as session:
            expired = list(
                session.scalars(
                    select(YouTubeReferenceRow.video_id).where(
                        YouTubeReferenceRow.expires_at <= (now or datetime.now(UTC))
                    )
                )
            )
            session.execute(
                delete(YouTubeReferenceRow).where(YouTubeReferenceRow.video_id.in_(expired))
            )
            return len(expired)

    def video_page(
        self, limit: int, cursor: str | None, now: datetime | None = None
    ) -> list[YouTubeReference]:
        self.prune(now)
        with self.sessions() as session:
            query = select(YouTubeReferenceRow).order_by(YouTubeReferenceRow.video_id).limit(limit)
            if cursor:
                query = query.where(YouTubeReferenceRow.video_id > cursor)
            return [
                YouTubeReference.model_validate(row.metadata_value)
                for row in session.scalars(query)
            ]

    def evidence(self, document_id: str) -> tuple[ArticleEvidence, ...]:
        with self.sessions() as session:
            values = session.scalars(
                select(ProviderEvidenceRow)
                .join(ProviderArticleRow)
                .where(ProviderArticleRow.document_id == document_id)
                .order_by(ProviderEvidenceRow.provider)
            )
            return tuple(
                ArticleEvidence.model_validate(
                    {
                        k: v
                        for k, v in row.metadata_value.items()
                        if k in ArticleEvidence.model_fields
                    }
                )
                for row in values
            )

    def article_page(self, limit: int, cursor: str | None) -> list[ProviderArticleView]:
        with self.sessions() as session:
            # An ingestion may complete before a status poll. Discover its canonical
            # document through the persisted ingestion idempotency key, read-only.
            from aegis.persistence.models import IngestionRow

            pending = session.execute(
                select(ProviderArticleRow, DocumentRow.document_id)
                .join(
                    IngestionRow,
                    (IngestionRow.source_id == ProviderArticleRow.source_id)
                    & (
                        IngestionRow.idempotency_key
                        == ProviderArticleRow.request["idempotency_key"].as_string()
                    ),
                )
                .join(DocumentRow, DocumentRow.ingestion_id == IngestionRow.ingestion_id)
                .where(
                    ProviderArticleRow.document_id.is_(None),
                    ProviderArticleRow.workflow_id.is_not(None),
                )
                .limit(100)
            )
            for row, document_id in pending:
                row.document_id = document_id
            session.commit()
            query = (
                select(ProviderArticleRow)
                .order_by(
                    ProviderArticleRow.acquired_at.desc(), ProviderArticleRow.article_id.desc()
                )
                .limit(limit)
            )
            if cursor:
                timestamp, identity = cursor.split("|", 1)
                cutoff = datetime.fromisoformat(timestamp)
                if cutoff.tzinfo is None or len(identity) != 36:
                    raise ValueError("invalid acquisition cursor")
                query = query.where(
                    (ProviderArticleRow.acquired_at < cutoff)
                    | (
                        (ProviderArticleRow.acquired_at == cutoff)
                        & (ProviderArticleRow.article_id < identity)
                    )
                )
            rows = list(session.scalars(query))
            by_article: dict[str, list[ProviderEvidenceRow]] = {}
            for evidence_row in session.scalars(
                select(ProviderEvidenceRow)
                .where(ProviderEvidenceRow.article_id.in_([r.article_id for r in rows]))
                .order_by(ProviderEvidenceRow.provider)
            ):
                by_article.setdefault(evidence_row.article_id, []).append(evidence_row)
            results = []
            for row in rows:
                evidence = by_article.get(row.article_id, [])
                results.append(
                    ProviderArticleView(
                        document_id=row.document_id,
                        title=row.title,
                        source_id=row.source_id,
                        published_at=utc(row.published_at) if row.published_at else None,
                        workflow_id=row.workflow_id,
                        acquired_at=utc(row.acquired_at),
                        article_id=row.article_id,
                        evidence=tuple(
                            ArticleEvidence.model_validate(
                                {
                                    k: v
                                    for k, v in e.metadata_value.items()
                                    if k in ArticleEvidence.model_fields
                                }
                            )
                            for e in evidence
                        ),
                    )
                )
            return results

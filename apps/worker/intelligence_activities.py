"""Retryable product activities; model loading and database I/O never enter workflows."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from temporalio import activity

from aegis.ingestion.service import IngestionService
from aegis.intelligence.engine import IntelligenceEngine
from aegis.intelligence.errors import IntelligenceError
from aegis.intelligence.pipeline import AnalysisPipeline, stable_id
from aegis.observability.logging import correlation_id_context
from aegis.provenance.service import canonical
from aegis.security.crypto import EncryptedPayload

logger = logging.getLogger("aegis.worker")


class IntelligenceActivities:
    def __init__(
        self, ingestion: IngestionService, engine: IntelligenceEngine, pipeline: AnalysisPipeline
    ) -> None:
        self.ingestion, self.engine, self.pipeline = ingestion, engine, pipeline

    async def analyze(
        self, task: str, document_id: str, run_key: str, correlation_id: str
    ) -> dict[str, str]:
        token = correlation_id_context.set(correlation_id)
        try:
            analysis_id = stable_id("ana", f"{run_key}:{task}")
            if await asyncio.to_thread(self.pipeline.existing, analysis_id):
                return {"analysis_id": analysis_id, "status": "completed"}
            document = await asyncio.to_thread(self.ingestion.repository.get_document, document_id)
            try:
                match task:
                    case "entities":
                        result = await self.engine.entities.extract(document)
                    case "topics":
                        result = await self.engine.topics.classify(document)
                    case "sentiment":
                        result = await self.engine.sentiment.analyze(document)
                    case "embedding":
                        result = await self.engine.embeddings.embed(document)
                    case "resolution" | "events":
                        mentions, candidates = await asyncio.to_thread(
                            self.pipeline.context,
                            document_id,
                            stable_id("ana", f"{run_key}:entities"),
                        )
                        if task == "resolution":
                            result = await self.engine.resolver.resolve(
                                document, mentions, candidates
                            )
                        else:
                            result = await self.engine.events.extract(document, ())
                    case _:
                        raise ValueError("unknown AI task")
            except IntelligenceError as exc:
                logger.warning(
                    "ai_stage_unavailable", extra={"stage": task, "error_type": type(exc).__name__}
                )
                return {"status": "unavailable", "reason": type(exc).__name__}
            result = result.model_copy(update={"analysis_id": analysis_id})
            await asyncio.to_thread(self.pipeline.persist, document, result, correlation_id)
            logger.info("ai_stage_completed", extra={"stage": task})
            return {"analysis_id": analysis_id, "status": "completed"}
        finally:
            correlation_id_context.reset(token)

    @activity.defn(name="analyze_entities")
    async def entities(self, document_id: str, run_key: str, correlation_id: str) -> dict[str, str]:
        return await self.analyze("entities", document_id, run_key, correlation_id)

    @activity.defn(name="analyze_topics")
    async def topics(self, document_id: str, run_key: str, correlation_id: str) -> dict[str, str]:
        return await self.analyze("topics", document_id, run_key, correlation_id)

    @activity.defn(name="analyze_sentiment")
    async def sentiment(
        self, document_id: str, run_key: str, correlation_id: str
    ) -> dict[str, str]:
        return await self.analyze("sentiment", document_id, run_key, correlation_id)

    @activity.defn(name="generate_embedding")
    async def embedding(
        self, document_id: str, run_key: str, correlation_id: str
    ) -> dict[str, str]:
        return await self.analyze("embedding", document_id, run_key, correlation_id)

    @activity.defn(name="resolve_entities")
    async def resolution(
        self, document_id: str, run_key: str, correlation_id: str
    ) -> dict[str, str]:
        return await self.analyze("resolution", document_id, run_key, correlation_id)

    @activity.defn(name="extract_events")
    async def events(self, document_id: str, run_key: str, correlation_id: str) -> dict[str, str]:
        return await self.analyze("events", document_id, run_key, correlation_id)

    @activity.defn(name="record_provenance")
    async def provenance(self, document_id: str, run_key: str, analysis_ids: list[str]) -> str:
        document = await asyncio.to_thread(self.ingestion.repository.get_document, document_id)
        ingestion = await asyncio.to_thread(
            self.ingestion.repository.get_ingestion, document.ingestion_id
        )
        raw = await self.ingestion.storage.get_object(ingestion.object.key)
        media = await self.pipeline.media_snapshot(
            document_id, self.ingestion.storage, signing=True
        )
        provenance_id = await asyncio.to_thread(
            self.pipeline.sign, document_id, run_key, analysis_ids, raw, media
        )
        manifest = await asyncio.to_thread(self.pipeline.manifest, document_id, provenance_id)
        content = canonical(manifest.model_dump(mode="json"))
        key = f"provenance/encrypted/{provenance_id}.json"
        crypto = self.pipeline.provenance.crypto
        aad = document_id.encode()
        if await self.ingestion.storage.exists(key):
            encrypted = EncryptedPayload.model_validate_json(
                await self.ingestion.storage.get_object(key)
            )
            decrypted = await asyncio.to_thread(crypto.decrypt, encrypted, associated_data=aad)
            if decrypted != content:
                raise ValueError("encrypted provenance archive integrity failure")
        else:
            encrypted = await asyncio.to_thread(
                crypto.encrypt, content, key_id=self.pipeline.key_id, associated_data=aad
            )
            await self.ingestion.storage.put_object(
                key, encrypted.model_dump_json().encode(), "application/json"
            )
        return provenance_id

    def registered(self) -> list[Callable[..., Any]]:
        return [
            self.entities,
            self.topics,
            self.sentiment,
            self.embedding,
            self.resolution,
            self.events,
            self.provenance,
        ]

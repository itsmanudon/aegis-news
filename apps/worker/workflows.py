"""Deterministic orchestration; I/O, clocks, parsing and IDs belong to activities."""

import json
from datetime import timedelta
from typing import cast

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities import foundation_echo


@workflow.defn
class FoundationWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            foundation_echo, name, start_to_close_timeout=timedelta(seconds=10)
        )


@workflow.defn
class NewsIngestionWorkflow:
    @workflow.run
    async def run(self, request_json: str) -> dict[str, str]:
        retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=5,
            non_retryable_error_types=["InvalidIngestion"],
        )
        ingestion_id = await workflow.execute_activity(
            "prepare_ingestion",
            args=[request_json, workflow.now().isoformat()],
            result_type=str,
            start_to_close_timeout=timedelta(seconds=60),
            schedule_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry,
        )
        document_json = await workflow.execute_activity(
            "normalize_ingestion",
            ingestion_id,
            result_type=str,
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=3),
            retry_policy=retry,
        )
        result = await workflow.execute_activity(
            "commit_ingestion",
            document_json,
            result_type=dict[str, str],
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=3),
            retry_policy=retry,
        )
        result = cast(dict[str, str], result)
        # JSON parsing and workflow identity are deterministic. All inference, clocks,
        # storage, cryptography and SQL operations remain in independently retryable activities.
        correlation_id = json.loads(request_json).get("correlation_id", "ingestion")
        run_key = workflow.info().workflow_id
        analysis_ids = []
        for name in (
            "analyze_entities",
            "analyze_topics",
            "analyze_sentiment",
            "generate_embedding",
            "resolve_entities",
            "extract_events",
        ):
            outcome = await workflow.execute_activity(
                name,
                args=[result["document_id"], run_key, correlation_id],
                result_type=dict[str, str],
                start_to_close_timeout=timedelta(minutes=3),
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry,
            )
            result[name] = outcome["status"]
            if "analysis_id" in outcome:
                analysis_ids.append(outcome["analysis_id"])
        result["provenance_id"] = await workflow.execute_activity(
            "record_provenance",
            args=[result["document_id"], run_key, analysis_ids],
            result_type=str,
            start_to_close_timeout=timedelta(seconds=60),
            schedule_to_close_timeout=timedelta(minutes=3),
            retry_policy=retry,
        )
        return result

"""Connectivity demonstration only; no news processing side effects."""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities import foundation_echo


@workflow.defn
class FoundationWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            foundation_echo, name, start_to_close_timeout=timedelta(seconds=10)
        )

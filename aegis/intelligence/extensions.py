"""Supplemental capabilities, without changing the frozen v1 ports."""

from typing import Protocol, runtime_checkable

from aegis.domain.models import AnalysisResult, NewsDocument, NewsEvent


@runtime_checkable
class EventClassifier(Protocol):
    async def classify(self, document: NewsDocument, event: NewsEvent) -> AnalysisResult: ...

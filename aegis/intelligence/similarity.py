"""Small CPU similarity helper over canonical analyses, with temporal/space checks."""

import math
from datetime import datetime

from aegis.domain.models import AnalysisResult, EmbeddingResult


def vector(analysis: AnalysisResult) -> tuple[float, ...]:
    AnalysisResult.model_validate(analysis.model_dump())
    if analysis.analysis_type != "embedding" or len(analysis.outputs) != 1:
        raise ValueError("expected exactly one embedding output")
    output = analysis.outputs[0]
    if not isinstance(output, EmbeddingResult):
        raise ValueError("expected embedding output")
    return output.values


def similar_analyses(
    query: AnalysisResult,
    candidates: tuple[AnalysisResult, ...],
    *,
    as_of: datetime,
    limit: int = 10,
) -> tuple[tuple[str, float], ...]:
    if as_of.tzinfo is None or as_of.utcoffset() is None or limit < 1:
        raise ValueError("aware as_of and positive limit required")
    values = vector(query)
    if query.available_at > as_of:
        raise ValueError("query analysis was unavailable at requested time")
    space = (query.provider, query.model_name, query.model_version, query.configuration_hash)
    results = []
    for candidate in candidates:
        if candidate.analysis_type != "embedding" or candidate.available_at > as_of:
            continue
        if (
            candidate.provider,
            candidate.model_name,
            candidate.model_version,
            candidate.configuration_hash,
        ) != space:
            continue
        other = vector(candidate)
        if len(other) != len(values):
            raise ValueError("matching embedding metadata has inconsistent dimensions")
        denominator = math.sqrt(sum(v * v for v in values) * sum(v * v for v in other))
        similarity = (
            sum(a * b for a, b in zip(values, other, strict=True)) / denominator
            if (denominator)
            else 0.0
        )
        results.append((candidate.analysis_id, max(-1.0, min(1.0, similarity))))
    return tuple(sorted(results, key=lambda item: (-item[1], item[0]))[:limit])

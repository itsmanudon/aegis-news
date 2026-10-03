"""Explicit model-output materialization; never upgrades predictions into facts."""

from uuid import NAMESPACE_URL, uuid5

from aegis.domain.models import AnalysisResult, EntityExtractionResult, EntityMention, NewsDocument


def materialize_mentions(
    document: NewsDocument, analysis: AnalysisResult
) -> tuple[EntityMention, ...]:
    AnalysisResult.model_validate(analysis.model_dump())
    if (
        analysis.analysis_type != "entity_extraction"
        or analysis.document_id != document.document_id
    ):
        raise ValueError("expected entity extraction analysis for this document")
    mentions = []
    for index, output in enumerate(analysis.outputs):
        if not isinstance(output, EntityExtractionResult):
            raise ValueError("expected entity extraction output")
        if document.text[output.start_offset : output.end_offset] != output.surface:
            raise ValueError("extraction evidence does not match document revision")
        mentions.append(
            EntityMention(
                mention_id=f"mention_{uuid5(NAMESPACE_URL, f'{analysis.analysis_id}:{index}')}",
                document_id=analysis.document_id,
                surface=output.surface,
                start_offset=output.start_offset,
                end_offset=output.end_offset,
                evidence_kind="model_output",
                analysis_id=analysis.analysis_id,
            )
        )
    return tuple(mentions)

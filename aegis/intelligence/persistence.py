"""Append to existing immutable analyses; transaction/foreign-key ownership stays with caller."""

from sqlalchemy.orm import Session

from aegis.domain.models import AnalysisResult
from aegis.persistence.models import AnalysisRow


def append_analysis(session: Session, analysis: AnalysisResult) -> AnalysisRow:
    validated = AnalysisResult.model_validate(analysis.model_dump())
    row = AnalysisRow(
        **validated.model_dump(mode="python", exclude={"outputs"}),
        outputs=[o.model_dump(mode="json") for o in validated.outputs],
    )
    # Deliberately add, never merge/upsert/update. DB duplicate-ID and immutable-row
    # constraints remain authoritative; the caller commits or rolls back atomically.
    session.add(row)
    return row


def from_row(row: AnalysisRow) -> AnalysisResult:
    return AnalysisResult.model_validate(
        {name: getattr(row, name) for name in AnalysisResult.model_fields}
    )

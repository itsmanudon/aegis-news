"""Candidate-bounded entity resolution; ambiguity is explicitly unresolved."""

import re
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from difflib import SequenceMatcher

from aegis.domain.models import (
    AnalysisResult,
    Entity,
    EntityMention,
    EntityResolutionResult,
    NewsDocument,
)
from aegis.entities.spans import span_matches
from aegis.intelligence.common import envelope, validate_document
from aegis.intelligence.config import ModelSpec


def normalized_name(name: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", name).casefold()))


class Resolver:
    def __init__(
        self,
        aliases: Mapping[str, tuple[str, ...]] | None = None,
        identifiers: Mapping[str, tuple[str, ...]] | None = None,
        threshold: float = 0.86,
        ambiguity_margin: float = 0.08,
    ) -> None:
        if not 0 <= threshold <= 1 or not 0 <= ambiguity_margin <= 1:
            raise ValueError("resolution thresholds must be in [0, 1]")
        self.aliases = tuple(sorted((k, tuple(v)) for k, v in (aliases or {}).items()))
        self.identifiers = tuple(sorted((k, tuple(v)) for k, v in (identifiers or {}).items()))
        self.threshold, self.ambiguity_margin = threshold, ambiguity_margin
        self.spec = ModelSpec(backend="baseline", model_name="candidate-resolver", revision="1")

    def rank(self, surface: str, candidates: tuple[Entity, ...]) -> tuple[tuple[str, float], ...]:
        if len({c.entity_id for c in candidates}) != len(candidates):
            raise ValueError("duplicate candidate IDs")
        aliases, identifiers = dict(self.aliases), dict(self.identifiers)
        normalized = normalized_name(surface)
        if not normalized:
            return ()
        ranks = []
        for candidate in candidates:
            Entity.model_validate(candidate.model_dump())
            names = (candidate.canonical_name, *aliases.get(candidate.entity_id, ()))
            if surface.strip().casefold() in (
                v.strip().casefold() for v in identifiers.get(candidate.entity_id, ())
            ) or any(normalized == normalized_name(n) for n in names):
                score = 1.0
            else:
                score = max(
                    SequenceMatcher(None, normalized, normalized_name(n)).ratio() for n in names
                )
                # Short fuzzy names are especially prone to false merges.
                if len(normalized) < 5:
                    score = 0.0
            ranks.append((candidate.entity_id, score))
        return tuple(sorted(ranks, key=lambda item: (-item[1], item[0])))

    def choose(self, ranks: tuple[tuple[str, float], ...]) -> tuple[str | None, float]:
        if not ranks:
            return None, 0.0
        entity_id, score = ranks[0]
        if score < self.threshold or (
            len(ranks) > 1 and (score == ranks[1][1] or score - ranks[1][1] < self.ambiguity_margin)
        ):
            return None, 0.0
        return entity_id, score

    async def resolve(
        self,
        document: NewsDocument,
        mentions: tuple[EntityMention, ...],
        candidates: tuple[Entity, ...],
    ) -> AnalysisResult:
        validate_document(document)
        started = datetime.now(UTC)
        outputs = []
        for mention in mentions:
            EntityMention.model_validate(mention.model_dump())
            if mention.document_id != document.document_id:
                raise ValueError("mention belongs to another document")
            if not span_matches(
                document.text, mention.surface, mention.start_offset, mention.end_offset
            ):
                raise ValueError("mention evidence does not match document")
            entity_id, score = self.choose(self.rank(mention.surface, candidates))
            outputs.append(
                EntityResolutionResult(
                    mention_id=mention.mention_id, entity_id=entity_id, confidence=score
                )
            )
        return envelope(
            document,
            self.spec,
            tuple(outputs),
            started,
            {"resolver": "1"},
            context={
                "aliases": self.aliases,
                "identifiers": self.identifiers,
                "threshold": self.threshold,
                "ambiguity_margin": self.ambiguity_margin,
                "candidates": [c.model_dump(mode="json") for c in candidates],
                "mention_analyses": [m.analysis_id for m in mentions],
            },
        )

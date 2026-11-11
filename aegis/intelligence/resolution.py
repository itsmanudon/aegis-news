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


# Legal forms that news text routinely drops: "Apple" for "Apple Inc.". Only trailing
# legal forms are removed. Words such as "group" or "holdings" stay, because they
# distinguish real companies from each other.
LEGAL_FORMS = frozenset(
    [
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "plc",
        "llc",
        "lp",
        "llp",
        "ag",
        "se",
        "sa",
        "nv",
        "bv",
        "gmbh",
        "spa",
        "ab",
        "asa",
        "oyj",
        "pvt",
        "private",
    ]
)


def match_keys(name: str) -> tuple[str, ...]:
    """Keys a name is stored and looked up under: its normalized form and its core.

    The core drops a leading article and trailing legal forms, never the last word.
    Lookup is by equality on these keys, which an index answers whatever the number of
    entities; similarity scoring then runs only over the few candidates found.
    """
    full = normalized_name(name)
    words = full.split()
    if len(words) > 1 and words[0] == "the":
        words = words[1:]
    while len(words) > 1 and words[-1] in LEGAL_FORMS:
        words.pop()
    return tuple(dict.fromkeys(key for key in (full, " ".join(words)) if key))


def written_in(surface: str, names: tuple[str, ...]) -> bool:
    """True when ``surface`` appears as whole words, same capitalisation, in a name."""
    pattern = re.compile(r"(?<!\w)" + re.escape(surface.strip()) + r"(?!\w)")
    return any(pattern.search(name) for name in names)


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
        # Revision 2: a name also matches on its core key (legal forms dropped).
        # Revision 3: a mention whose extracted kind differs from the candidate's never
        # matches, and a short name matches only as written.
        self.spec = ModelSpec(backend="baseline", model_name="candidate-resolver", revision="3")

    def rank(
        self,
        surface: str,
        candidates: tuple[Entity, ...],
        aliases: Mapping[str, tuple[str, ...]] | None = None,
        kind: str | None = None,
    ) -> tuple[tuple[str, float], ...]:
        if len({c.entity_id for c in candidates}) != len(candidates):
            raise ValueError("duplicate candidate IDs")
        aliases = dict(self.aliases) if aliases is None else aliases
        identifiers = dict(self.identifiers)
        normalized = normalized_name(surface)
        if not normalized:
            return ()
        keys = set(match_keys(surface))
        ranks = []
        for candidate in candidates:
            Entity.model_validate(candidate.model_dump())
            names = (candidate.canonical_name, *aliases.get(candidate.entity_id, ()))
            # The extractor said this is a person or a place: it is not this company.
            # "other" is what the offline extractor says of every span, so it decides nothing.
            if kind not in (None, "other") and kind != candidate.kind:
                ranks.append((candidate.entity_id, 0.0))
                continue
            if surface.strip().casefold() in (
                v.strip().casefold() for v in identifiers.get(candidate.entity_id, ())
            ) or any(keys & set(match_keys(n)) for n in names):
                # "SAP" names a company; "sap" does not. A name of four characters or
                # fewer matches only where it appears with the same capitalisation.
                score = 1.0 if len(normalized) > 4 or written_in(surface, names) else 0.0
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
        aliases: Mapping[str, tuple[str, ...]] | None = None,
        kinds: Mapping[str, str | None] | None = None,
    ) -> AnalysisResult:
        """Resolve mentions against ``candidates``.

        ``kinds`` maps a mention id to the kind its extraction predicted, when known.

        ``aliases`` are stored names for these candidates, supplied per call by the
        caller that looked the candidates up. They add to the aliases the resolver was
        built with.
        """
        validate_document(document)
        started = datetime.now(UTC)
        known = {**dict(self.aliases), **{k: tuple(v) for k, v in (aliases or {}).items()}}
        outputs = []
        for mention in mentions:
            EntityMention.model_validate(mention.model_dump())
            if mention.document_id != document.document_id:
                raise ValueError("mention belongs to another document")
            if not span_matches(
                document.text, mention.surface, mention.start_offset, mention.end_offset
            ):
                raise ValueError("mention evidence does not match document")
            entity_id, score = self.choose(
                self.rank(mention.surface, candidates, known, (kinds or {}).get(mention.mention_id))
            )
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
            {"resolver": "3"},
            context={
                "aliases": tuple(sorted(known.items())),
                "identifiers": self.identifiers,
                "threshold": self.threshold,
                "ambiguity_margin": self.ambiguity_margin,
                "candidates": [c.model_dump(mode="json") for c in candidates],
                "mention_analyses": [m.analysis_id for m in mentions],
            },
        )

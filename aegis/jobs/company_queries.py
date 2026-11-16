"""Company searches for the daily job: the seeded companies, packed into queries.

The general query ("stocks OR markets OR earnings") rarely names a seeded company,
so most StockViz symbols never got news. This builds provider queries from the
seed file instead: each company's search name (its shortest usable alias, else
its name without legal forms), multi-word names quoted, joined with OR and packed
into as few queries as fit the provider's 100-character limit. 161 companies fit
in 23 queries, one provider request each.

The queries only fetch candidates. Whether a document links to a company is still
decided by entity extraction and the candidate resolver.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

from aegis.entities.registry import InstrumentSeed
from aegis.intelligence.resolution import LEGAL_FORMS

MAX_QUERY_LENGTH = 100  # FetchOptions.query; NewsData's free tier allows 100 characters
MIN_ALIAS_LENGTH = 4  # shorter aliases ("GE", "SBI") are usually tickers or ambiguous


def search_name(seed: InstrumentSeed) -> str:
    """The name a headline most likely uses for this company."""
    usable = [a for a in seed.aliases if len(a) >= MIN_ALIAS_LENGTH]
    if usable:
        return min(usable, key=len)
    words = seed.name.replace(",", " ").split()
    if len(words) > 1 and words[0].lower() == "the":
        words = words[1:]
    while len(words) > 1 and re.sub(r"[^\w]", "", words[-1].lower()) in LEGAL_FORMS:
        words.pop()
    if len(words) > 1 and words[-1] in {"&", "and"}:
        words.pop()
    # A long name is written by its acronym ("BMW", "AMD", "TCS").
    acronyms = [a for a in seed.aliases if len(a) == MIN_ALIAS_LENGTH - 1]
    if acronyms and len(words) >= 3:
        return acronyms[0]
    return " ".join(words)


def _term(name: str) -> str:
    return f'"{name}"' if re.search(r"[^\w.-]", name) else name


def company_queries(
    seeds: Sequence[InstrumentSeed], max_length: int = MAX_QUERY_LENGTH
) -> list[str]:
    """Every seeded company's search name, OR-joined into queries in seed order."""
    queries: list[str] = []
    current = ""
    seen: set[str] = set()
    for seed in seeds:
        name = search_name(seed)
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        term = _term(name)
        if len(term) > max_length:
            continue
        joined = f"{current} OR {term}" if current else term
        if len(joined) <= max_length:
            current = joined
        else:
            queries.append(current)
            current = term
    if current:
        queries.append(current)
    return queries


def todays_queries(queries: Sequence[str], requests: int, day: date) -> list[str]:
    """``requests`` queries for this day. With fewer requests than queries, each day
    starts where the previous one stopped, so every company comes round in turn."""
    if requests <= 0 or not queries:
        return []
    if requests >= len(queries):
        return list(queries)
    start = (day.toordinal() * requests) % len(queries)
    return [queries[(start + i) % len(queries)] for i in range(requests)]


def load_seeds(path: Path) -> list[InstrumentSeed]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TypeAdapter(list[InstrumentSeed]).validate_python(raw)

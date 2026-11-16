"""Company searches for the daily job (owner-approved NewsData allowance, 16 Nov 2026)."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from aegis.entities.registry import InstrumentSeed
from aegis.jobs.company_queries import (
    MAX_QUERY_LENGTH,
    company_queries,
    load_seeds,
    search_name,
    todays_queries,
)
from aegis.jobs.daily import JobReport, planned_company_queries
from aegis.providers.models import FetchOptions, ProviderOutcome, ProviderRun
from aegis.settings import Settings

SEED = Path("data/instruments/stockviz.json")


def seed(name, *aliases):
    return InstrumentSeed(name=name, aliases=aliases)


def test_search_names_are_what_headlines_write():
    assert search_name(seed("Apple Inc.")) == "Apple"
    assert search_name(seed("The Home Depot, Inc.")) == "Home Depot"
    assert search_name(seed("JPMorgan Chase & Co.", "JPMorgan", "JP Morgan")) == "JPMorgan"
    assert search_name(seed("Bayerische Motoren Werke AG", "BMW")) == "BMW"
    assert search_name(seed("Reliance Industries Limited", "Reliance")) == "Reliance"
    # A short alias of a short name is not used: "GE" alone is too ambiguous.
    assert search_name(seed("GE Aerospace", "GE", "General Electric")) == "General Electric"


def test_queries_quote_phrases_and_fit_the_provider_limit():
    queries = company_queries(
        [seed("Apple Inc."), seed("Bank of America Corporation"), seed("AT&T Inc.")]
    )
    assert queries == ['Apple OR "Bank of America" OR "AT&T"']


def test_every_stockviz_company_is_searched_and_every_query_is_valid():
    seeds = load_seeds(SEED)
    queries = company_queries(seeds)
    assert len(queries) <= 30
    for query in queries:
        assert len(query) <= MAX_QUERY_LENGTH
        FetchOptions(query=query, limit=10)
    joined = " OR ".join(queries)
    for s in seeds:
        assert search_name(s) in joined, s.name


def test_fewer_requests_rotate_through_every_query():
    queries = [f"q{i}" for i in range(10)]
    assert todays_queries(queries, 0, date(2026, 11, 16)) == []
    assert todays_queries(queries, 20, date(2026, 11, 16)) == queries
    day = date(2026, 11, 16)
    seen = set()
    for offset in range(5):
        today = todays_queries(queries, 2, date.fromordinal(day.toordinal() + offset))
        assert len(today) == 2
        seen.update(today)
    assert seen == set(queries)


def test_settings_bound_the_allowance():
    for changes in ({"job_company_requests": 51}, {"job_company_requests": 5}):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **changes)
    Settings(_env_file=None, job_company_requests=24, job_company_file=SEED)


def test_planned_queries_are_off_by_default_and_say_why_a_file_failed(tmp_path):
    day = date(2026, 11, 16)
    assert planned_company_queries(Settings(_env_file=None), day) == ([], None)
    on = Settings(_env_file=None, job_company_requests=24, job_company_file=SEED)
    queries, error = planned_company_queries(on, day)
    assert error is None and queries == company_queries(load_seeds(SEED))
    missing = on.model_copy(update={"job_company_file": tmp_path / "none.json"})
    assert planned_company_queries(missing, day) == ([], "FileNotFoundError")


def test_the_report_counts_company_runs():
    now = datetime(2026, 11, 16, tzinfo=UTC)
    ok = ProviderRun(
        run_id="a",
        created_at=now,
        status="submitted",
        outcomes=(ProviderOutcome(provider="newsdata", status="submitted"),),
    )
    budget = ok.model_copy(
        update={
            "outcomes": (
                ProviderOutcome(provider="newsdata", status="failed", error="daily_budget_reached"),
            )
        }
    )
    broken = ok.model_copy(
        update={"outcomes": (ProviderOutcome(provider="newsdata", status="failed", error="x"),)}
    )
    base = {"started_at": now, "finished_at": now, "run": ok}
    assert JobReport(**base, company_runs=(ok, budget)).ok
    assert not JobReport(**base, company_runs=(broken,)).ok
    assert not JobReport(**base, company_error="FileNotFoundError").ok

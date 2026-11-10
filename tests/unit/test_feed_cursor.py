"""Feed cursor handling. The database behaviour is covered in tests/integration/test_feed.py."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from aegis.intelligence import feed
from aegis.intelligence.read_models import pack

FILTERS = {"kind": "feed"}
DOCUMENT = f"doc_{UUID(int=7)}"


def test_position_round_trips_and_normalises_to_utc():
    moment = datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    decoded = feed.decode_position(feed.encode_position((moment, DOCUMENT), FILTERS), FILTERS)
    assert decoded == (moment.astimezone(UTC), DOCUMENT)
    assert decoded[0].utcoffset() == timedelta(0)


def test_start_position_is_a_valid_cursor():
    assert feed.decode_position(feed.encode_position(feed.START, FILTERS), FILTERS) == feed.START


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not base64!",
        "A" * (feed.CURSOR_MAXIMUM + 1),
        pack(["2026-01-01T00:00:00+00:00", DOCUMENT]),
        pack(
            {"v": 1, "kind": "feed", "filters": "0" * 64, "key": ["2026-01-01T00:00:00+00:00", ""]}
        ),
        pack({"v": 2, "kind": "feed", "filters": feed.fingerprint(FILTERS), "key": ["x", ""]}),
    ],
)
def test_malformed_or_foreign_cursors_are_rejected(value):
    with pytest.raises(ValueError):
        feed.decode_position(value, FILTERS)


@pytest.mark.parametrize(
    "key",
    [
        ["2026-01-01T00:00:00", DOCUMENT],  # no offset
        ["2026-01-01T00:00:00+00:00", "doc_not-a-uuid"],
        ["2026-01-01T00:00:00+00:00"],
        [None, DOCUMENT],
        "2026-01-01T00:00:00+00:00",
    ],
)
def test_cursor_keys_are_validated(key):
    value = pack({"v": 1, "kind": "feed", "filters": feed.fingerprint(FILTERS), "key": key})
    with pytest.raises(ValueError):
        feed.decode_position(value, FILTERS)


def test_cursor_is_bound_to_its_filters():
    cursor = feed.encode_position((datetime(2026, 1, 1, tzinfo=UTC), DOCUMENT), FILTERS)
    with pytest.raises(ValueError):
        feed.decode_position(cursor, {"kind": "feed", "venue": "XNAS"})

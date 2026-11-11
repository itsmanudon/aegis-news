"""Feed cursor handling. The database behaviour is covered in tests/integration/test_feed.py."""

from uuid import UUID

import pytest

from aegis.intelligence import feed
from aegis.intelligence.read_models import pack

FILTERS = {"kind": "feed"}
DOCUMENT = f"doc_{UUID(int=7)}"


def test_position_round_trips():
    position = (9_007_199_254_740_993, DOCUMENT)  # beyond 2**53: kept exact
    assert feed.decode_position(feed.encode_position(position, FILTERS), FILTERS) == position


def test_start_position_is_a_valid_cursor():
    assert feed.decode_position(feed.encode_position(feed.START, FILTERS), FILTERS) == feed.START


def key(value):
    return pack({"v": 2, "kind": "feed", "filters": feed.fingerprint(FILTERS), "key": value})


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not base64!",
        "A" * (feed.CURSOR_MAXIMUM + 1),
        pack([1, DOCUMENT]),
        pack({"v": 2, "kind": "feed", "filters": "0" * 64, "key": [1, ""]}),
        # A version 1 cursor, positioned by signing time, is no longer accepted.
        pack(
            {
                "v": 1,
                "kind": "feed",
                "filters": feed.fingerprint(FILTERS),
                "key": ["2026-01-01T00:00:00+00:00", ""],
            }
        ),
    ],
)
def test_malformed_or_foreign_cursors_are_rejected(value):
    with pytest.raises(ValueError):
        feed.decode_position(value, FILTERS)


@pytest.mark.parametrize(
    "value",
    [
        ["2026-01-01T00:00:00+00:00", DOCUMENT],
        [1, "doc_not-a-uuid"],
        [1],
        [None, DOCUMENT],
        [True, DOCUMENT],
        [1.5, DOCUMENT],
        [-2, DOCUMENT],
        "1",
    ],
)
def test_cursor_keys_are_validated(value):
    with pytest.raises(ValueError):
        feed.decode_position(key(value), FILTERS)


def test_cursor_is_bound_to_its_filters():
    cursor = feed.encode_position((1, DOCUMENT), FILTERS)
    with pytest.raises(ValueError):
        feed.decode_position(cursor, {"kind": "feed", "venue": "XNAS"})

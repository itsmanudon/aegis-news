import base64
from datetime import UTC, datetime

import pytest

from aegis.domain.ids import new_id
from aegis.ingestion.inputs import IngestionRequest, decode_content, fingerprint
from aegis.normalization.article import parse_article


def request(content=b"Title\n\nArticle body", **kwargs):
    return IngestionRequest(
        source_id=new_id("src"),
        idempotency_key="fixture",
        content_base64=base64.b64encode(content).decode(),
        **kwargs,
    )


def test_plain_text_title_and_body():
    article = parse_article(decode_content(request()), "text/plain")
    assert article.title == "Title"
    assert article.text == "Title\n\nArticle body"
    assert article.language is None
    assert article.published_at is None


def test_html_removes_scripts_and_extracts_language():
    article = parse_article(
        b'<html lang="en"><title> A &amp; B </title><script>evil()</script>'
        b"<style>bad</style><p>Hello</p><p>World</p></html>",
        "text/html",
    )
    assert article.title == "A & B"
    assert article.text == "Hello\nWorld"
    assert article.language == "en"


def test_json_preserves_publisher_timestamp():
    article = parse_article(
        b'{"title":"Notice","text":"Body","published_at":"1999-01-02T03:04:05Z"}',
        "application/json",
    )
    assert article.published_at == datetime(1999, 1, 2, 3, 4, 5, tzinfo=UTC)


@pytest.mark.parametrize(
    "content,mime",
    [
        (b"", "text/plain"),
        (b"\xff", "text/plain"),
        (b"\0x", "text/plain"),
        (b"[]", "application/json"),
        (b'{"title":"x","text":""}', "application/json"),
        (b'{"title":"x","text":"body","published_at":"2020-01-01"}', "application/json"),
        (b"<script>only script</script>", "text/html"),
        (b'{"title":"x","text":"\\u0000"}', "application/json"),
    ],
)
def test_invalid_content(content, mime):
    with pytest.raises(ValueError):
        parse_article(content, mime)


def test_fingerprint_ignores_correlation_but_includes_metadata():
    original = request()
    assert fingerprint(original) == fingerprint(original.model_copy(update={"correlation_id": "b"}))
    assert fingerprint(original) != fingerprint(original.model_copy(update={"title": "Changed"}))


def test_title_override_cannot_be_whitespace():
    with pytest.raises(ValueError):
        request(title="   ")


def test_type_and_payload_limits():
    from aegis.ingestion.inputs import (
        MAX_CONTENT_BYTES,
        MAX_REQUEST_BYTES,
        MediaInput,
        decode_media,
    )

    with pytest.raises(ValueError):
        request(content_type="application/octet-stream")
    with pytest.raises(ValueError):
        decode_content(request(content=b"x" * (MAX_CONTENT_BYTES + 1)))
    with pytest.raises(ValueError):
        decode_content(request().model_copy(update={"content_base64": "bad!"}))
    with pytest.raises(ValueError):
        decode_media(MediaInput(kind="image", content_type="image/png", content_base64="YWJj"))
    media = MediaInput(
        kind="attachment",
        content_type="text/plain",
        content_base64=base64.b64encode(b"x" * MAX_CONTENT_BYTES).decode(),
    )
    oversized = request(media=(media, media, media))
    assert len(oversized.model_dump_json()) > MAX_REQUEST_BYTES
    with pytest.raises(ValueError):
        decode_content(oversized)

import base64

import pytest

from aegis.domain.ids import new_id
from aegis.ingestion.importers import historical_requests, local_request


def test_jsonl_historical_import_is_stable_and_preserves_raw_lines(tmp_path):
    path = tmp_path / "history.jsonl"
    lines = [b'{"title":"One","text":"Body"}', b'{"title":"Two","text":"More"}']
    path.write_bytes(b"\n".join(lines) + b"\n")
    source = new_id("src")
    requests = list(historical_requests(path, source, "history-v1"))
    assert [base64.b64decode(r.content_base64) for r in requests] == lines
    assert [r.idempotency_key for r in requests] == ["history-v1:1", "history-v1:2"]
    assert requests == list(historical_requests(path, source, "history-v1"))


def test_json_array_and_local_media(tmp_path):
    history = tmp_path / "history.json"
    history.write_text('[{"title":"One","text":"Body"}]', encoding="utf-8")
    source = new_id("src")
    assert len(list(historical_requests(history, source, "dataset"))) == 1
    article = tmp_path / "article.html"
    article.write_bytes(b"<h1>Fixture</h1><p>Body</p>")
    attachment = tmp_path / "evidence.txt"
    attachment.write_bytes(b"evidence")
    req = local_request(article, source, "local", media_paths=[attachment])
    assert req.content_type == "text/html"
    assert req.media[0].kind == "attachment"
    assert base64.b64decode(req.media[0].content_base64) == b"evidence"


def test_bad_historical_record_reports_line(tmp_path):
    history = tmp_path / "history.jsonl"
    history.write_bytes(b'{"title":"ok","text":"Body"}\n[]\n')
    with pytest.raises(ValueError, match="record 2"):
        list(historical_requests(history, new_id("src"), "dataset"))


def test_unsupported_local_file(tmp_path):
    path = tmp_path / "file.exe"
    path.write_bytes(b"test")
    with pytest.raises(ValueError):
        local_request(path, new_id("src"), "local")

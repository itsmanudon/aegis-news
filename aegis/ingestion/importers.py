"""Offline local file adapters. Files are read by the CLI, never by API/worker input."""

import base64
import json
from collections.abc import Iterator, Sequence
from pathlib import Path

from aegis.ingestion.inputs import (
    MAX_CONTENT_BYTES,
    MAX_MEDIA_BYTES,
    IngestionRequest,
    MediaInput,
    decode_content,
    decode_media,
)
from aegis.normalization.article import parse_article

ARTICLE_MIMES = {
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".json": "application/json",
}
MEDIA_MIMES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}
MAX_DATASET_BYTES = 16 * 1024 * 1024


def bounded_read(path: Path, limit: int) -> bytes:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as handle:
        content = handle.read(limit + 1)
    if not content or len(content) > limit:
        raise ValueError("file size outside allowed range")
    return content


def local_request(
    path: Path,
    source_id: str,
    idempotency_key: str,
    *,
    media_paths: Sequence[Path] = (),
) -> IngestionRequest:
    mime = ARTICLE_MIMES.get(path.suffix.lower())
    if mime is None:
        raise ValueError("unsupported article extension")
    media = []
    for item in media_paths:
        media_mime = MEDIA_MIMES.get(item.suffix.lower())
        if media_mime is None:
            raise ValueError("unsupported media extension")
        attachment = MediaInput.model_validate(
            {
                "kind": "image" if media_mime.startswith("image/") else "attachment",
                "content_type": media_mime,
                "content_base64": base64.b64encode(bounded_read(item, MAX_MEDIA_BYTES)).decode(),
            }
        )
        decode_media(attachment)
        media.append(attachment)
    request = IngestionRequest.model_validate(
        {
            "source_id": source_id,
            "idempotency_key": idempotency_key,
            "content_type": mime,
            "content_base64": base64.b64encode(bounded_read(path, MAX_CONTENT_BYTES)).decode(),
            "media": media,
        }
    )
    parse_article(decode_content(request), mime)
    return request


def historical_requests(path: Path, source_id: str, dataset_key: str) -> Iterator[IngestionRequest]:
    """Immutable dataset namespace + one-based record ordinal are retry identities.

    JSONL preserves each exact physical line (minus newline). JSON arrays preserve
    their complete original file offline; per-article raw bytes are canonical JSON.
    """
    if path.suffix.lower() == ".jsonl":
        with path.open("rb") as handle:
            total = 0
            for ordinal, line in enumerate(
                iter(lambda: handle.readline(MAX_CONTENT_BYTES + 2), b""), 1
            ):
                total += len(line)
                if total > MAX_DATASET_BYTES:
                    raise ValueError("dataset exceeds size limit")
                if not line.strip():
                    continue
                yield historical_record(line.rstrip(b"\r\n"), source_id, dataset_key, ordinal)
    elif path.suffix.lower() == ".json":
        records = json.loads(bounded_read(path, MAX_DATASET_BYTES))
        if not isinstance(records, list):
            raise ValueError("historical JSON must contain an array")
        for ordinal, record in enumerate(records, 1):
            content = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
            yield historical_record(content, source_id, dataset_key, ordinal)
    else:
        raise ValueError("historical dataset must be JSON or JSONL")


def historical_record(
    content: bytes,
    source_id: str,
    dataset_key: str,
    ordinal: int,
) -> IngestionRequest:
    try:
        parse_article(content, "application/json")
        request = IngestionRequest(
            source_id=source_id,
            idempotency_key=f"{dataset_key}:{ordinal}",
            content_type="application/json",
            content_base64=base64.b64encode(content).decode(),
        )
        decode_content(request)
        return request
    except ValueError as exc:
        raise ValueError(f"invalid historical record {ordinal}") from exc

"""Failure, rights and persistence tests using synthetic fixtures, never public news."""

import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aegis.provenance.service import canonical
from aegis.showcase import acquisition, daily
from aegis.showcase.acquisition import AcquisitionError, Fetcher, article, parse_feed
from aegis.showcase.contracts import DailyExport, parse_export
from aegis.showcase.daily_contracts import KeyEntry, MediaLink, MediaReference, TrustRegistry
from aegis.showcase.site import APP, artifact_bytes, check_trust
from aegis.showcase.sources import REGISTRY
from aegis.showcase.state import GitHubState, StateError


@pytest.fixture
def previous():
    return parse_export((APP / "dataset.json").read_bytes())


@pytest.fixture
def signing(previous):
    key = Ed25519PrivateKey.generate()
    signer = daily.DailySigner(key, "daily-v1")
    trust = TrustRegistry(
        keys={
            "showcase": KeyEntry(public_key=previous.public_key, status="verify-only"),
            "daily-v1": KeyEntry(
                public_key=base64.b64encode(key.public_key().public_bytes_raw()).decode(),
                status="active",
            ),
        }
    )
    return signer, trust


def metadata(source="nasa", title="Artemis Fixture News", suffix="fixture"):
    now = datetime.now(UTC) - timedelta(seconds=5)
    return article(
        source,
        title,
        "https://" + REGISTRY[source].hosts[0] + "/" + suffix,
        now - timedelta(hours=1),
        now,
        categories=(REGISTRY[source].coverage,),
    )


@pytest.fixture
async def release(previous, signing, monkeypatch):
    monkeypatch.setattr(
        daily,
        "acquire",
        AsyncMock(
            return_value=(
                [metadata(), metadata("federal-reserve", "Fixture Interest News", "fixture-rate")],
                {"nasa": "ok"},
            )
        ),
    )
    monkeypatch.setattr(daily, "media", AsyncMock(return_value=[]))
    async with httpx.AsyncClient() as client:
        export, _ = await daily.candidate(
            previous, *signing, Fetcher(client, spacing=0), datetime.now(UTC)
        )
    assert export
    return export


def resign(value, signing):
    value["release_signature"] = base64.b64encode(
        signing[0].private.sign(
            canonical({k: v for k, v in value.items() if k != "release_signature"})
        )
    ).decode()
    return value


@pytest.mark.asyncio
async def test_signed_multisource_release_preserves_legacy_bytes(previous, release):
    assert isinstance(parse_export(canonical(release.model_dump(mode="json"))), DailyExport)
    old = {r.metadata.id: r for r in previous.records}
    for r in release.records:
        if r.metadata.id in old:
            assert r.model_dump(mode="json") == old[r.metadata.id].model_dump(mode="json")
    assert {r.metadata.publisher for r in release.records} >= {"NASA", "Federal Reserve Board"}
    assert release.parent_sha256 == daily.digest(previous)
    assert artifact_bytes(release) == artifact_bytes(release)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "part", ["membership", "metadata", "analysis", "signature", "chain", "parent", "key", "media"]
)
async def test_release_tampering_fails(release, part):
    raw = release.model_dump(mode="json")
    if part == "membership":
        raw["records"].pop()
    elif part == "metadata":
        raw["records"][0]["metadata"]["title"] += " altered"
    elif part == "analysis":
        raw["records"][0]["analyses"][0]["outputs"][0]["confidence"] = 0.123
    elif part == "signature":
        raw["records"][0]["provenance"]["signature"] = "A" * 88
    elif part == "chain":
        raw["records"][0]["provenance"]["chain_hashes"][0] = "0" * 64
    elif part == "parent":
        raw["parent_sha256"] = "0" * 64
    elif part == "media":
        raw["media"] = [{"body": "unlicensed"}]
    else:
        raw["trust"]["keys"]["daily-v1"]["public_key"] = "A" * 44
    with pytest.raises(ValueError):
        parse_export(canonical(raw))


@pytest.mark.asyncio
async def test_resigned_bad_record_and_revocation_fail(release, signing):
    raw = release.model_dump(mode="json")
    raw["records"][0]["metadata"]["title"] += " altered"
    with pytest.raises(ValueError):
        parse_export(canonical(resign(raw, signing)))
    raw = release.model_dump(mode="json")
    raw["trust"]["keys"]["showcase"]["status"] = "revoked"
    with pytest.raises(ValueError):
        parse_export(canonical(resign(raw, signing)))
    with pytest.raises(ValueError, match="registry"):
        check_trust(release)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.nasa.gov/f",
        "https://127.0.0.1/f",
        "https://www.nasa.gov.evil.test/f",
        "https://www.nasa.gov/f?api_key=abc",
    ],
)
def test_unapproved_source_links_fail(url):
    with pytest.raises(ValueError):
        article("nasa", "Fixture", url, None, datetime.now(UTC))


def test_feed_parsing_dates_html_and_xml_safety():
    now = datetime.now(UTC)
    rss = (
        b"<rss><channel><item><title>&lt;b&gt;Fixture&lt;/b&gt; &amp; News</title>"
        b"<link>https://www.nasa.gov/fixture</link>"
        b"<pubDate>Wed, 14 Oct 2026 12:00:00 GMT</pubDate></item>"
        b"<item><title>Invalid</title><link>https://evil.test/</link></item></channel></rss>"
    )
    rows = parse_feed("nasa", rss, now)
    assert len(rows) == 1 and rows[0].title == "Fixture & News"
    assert rows[0].published_at == datetime(2026, 10, 14, 12, tzinfo=UTC)
    with pytest.raises(AcquisitionError):
        parse_feed("nasa", b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>', now)
    assert acquisition.timestamp("invalid") is None
    assert acquisition.timestamp("2026-10-14T12:00:00") is None


@pytest.mark.asyncio
async def test_transport_limits_redirects_and_retry_budget(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(acquisition.asyncio, "sleep", sleep)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(429, headers={"retry-after": "40"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        fetcher = Fetcher(client, spacing=0)
        with pytest.raises(AcquisitionError):
            await fetcher.get(REGISTRY["gdelt"].endpoint)
        assert len(calls) == 3
        assert 40 in [c.args[0] for c in sleep.call_args_list]
        assert 60 in [c.args[0] for c in sleep.call_args_list]
        with pytest.raises(AcquisitionError, match="unapproved"):
            await fetcher.get("https://127.0.0.1/private")
        fetcher.requests = 18
        with pytest.raises(AcquisitionError, match="ceiling"):
            await fetcher.get(REGISTRY["nasa"].endpoint)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,headers,body",
    [
        (302, {"location": "https://127.0.0.1/"}, b""),
        (403, {}, b""),
        (429, {"retry-after": "3600"}, b""),
        pytest.param(200, {}, b"x" * (2 * 1024 * 1024 + 1), id="oversized"),
    ],
)
async def test_transport_fails_closed(status, headers, body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(status, headers=headers, content=body)
        )
    ) as client:
        fetcher = Fetcher(client, spacing=0)
        with pytest.raises(AcquisitionError):
            await fetcher.get(REGISTRY["nasa"].endpoint)
        assert fetcher.requests == 1


@pytest.mark.asyncio
async def test_provider_failure_old_dates_and_unknown_publication(monkeypatch):
    now = datetime.now(UTC)
    old = (
        "<rss><channel><item><title>Fixture Old</title>"
        "<link>https://www.nasa.gov/old</link>"
        "<pubDate>Wed, 01 Jan 2020 12:00:00 GMT</pubDate></item></channel></rss>"
    )
    usgs = {
        "features": [
            {
                "properties": {
                    "title": "M 4.5 Fixture",
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/fixture",
                    "time": int((now - timedelta(hours=1)).timestamp() * 1000),
                    "updated": int((now - timedelta(minutes=5)).timestamp() * 1000),
                }
            }
        ]
    }

    async def get(endpoint, params=None):
        if endpoint == REGISTRY["usgs"].endpoint:
            return canonical(usgs)
        if endpoint == REGISTRY["nasa"].endpoint:
            return old.encode()
        raise AcquisitionError("unavailable")

    fetcher = Fetcher(httpx.AsyncClient(), spacing=0)
    monkeypatch.setattr(fetcher, "get", get)
    rows, outcomes = await acquisition.acquire(fetcher, now, 2)
    assert len(rows) == 1 and rows[0].published_at is None
    assert rows[0].occurred_at and rows[0].source_updated_at
    assert rows[0].discovered_at is None
    assert "unavailable" in outcomes["gdelt"]
    await fetcher.client.aclose()


@pytest.mark.asyncio
async def test_restart_deduplication_and_no_fabricated_refresh(release, signing, monkeypatch):
    new = [r.metadata for r in release.records if r.provenance.key_id == "daily-v1"]
    monkeypatch.setattr(daily, "acquire", AsyncMock(return_value=(new, {})))
    media = AsyncMock(return_value=[])
    monkeypatch.setattr(daily, "media", media)
    async with httpx.AsyncClient() as client:
        result, report = await daily.candidate(
            release, *signing, Fetcher(client), datetime.now(UTC)
        )
    assert result is None and report["new_selected"] == 0
    media.assert_not_called()


def test_diversity_and_per_publisher_ceiling():
    rows = [
        metadata(s, f"Fixture {i}", f"fixture-{i}")
        for s in ("nasa", "federal-reserve")
        for i in range(16)
    ]
    result = daily.balanced(rows, 48)
    assert len(result) == 16
    assert {r.publisher for r in result[:2]} == {"NASA", "Federal Reserve Board"}


@pytest.mark.parametrize(
    "ref,repo",
    [
        ("refs/pull/3/merge", "itsmanudon/aegis-news"),
        ("refs/heads/feature", "itsmanudon/aegis-news"),
        ("refs/heads/main", "attacker/fork"),
    ],
)
def test_signing_rejects_untrusted_actions(signing, monkeypatch, ref, repo):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF", ref)
    monkeypatch.setenv("GITHUB_REPOSITORY", repo)
    with pytest.raises(ValueError, match="trusted"):
        daily.signer(None, signing[1])


def test_missing_mismatched_and_revoked_signing_credentials(signing, monkeypatch):
    monkeypatch.delenv("AEGIS_PUBLIC_SIGNING_KEY", raising=False)
    with pytest.raises(ValueError, match="unavailable"):
        daily.signer(None, signing[1])
    monkeypatch.setenv(
        "AEGIS_PUBLIC_SIGNING_KEY",
        base64.b64encode(Ed25519PrivateKey.generate().private_bytes_raw()).decode(),
    )
    with pytest.raises(ValueError, match="match"):
        daily.signer(None, signing[1])


@pytest.fixture
def image():
    url = "https://commons.wikimedia.org/wiki/File:Artemis_Fixture.jpg"
    now = datetime.now(UTC) - timedelta(seconds=5)
    return dict(
        id=__import__("hashlib").sha256(url.encode()).hexdigest(),
        kind="image",
        title="Artemis Fixture",
        source_url=url,
        asset_url="https://upload.wikimedia.org/fixture.jpg",
        creator="Fixture Creator",
        license="Public Domain",
        license_url=url + "#Licensing",
        alt="Artemis Fixture",
        relationship_term="Artemis",
        acquired_at=now,
        refreshed_at=now,
        platform_id="123",
        publisher="Wikimedia Commons",
    )


def test_item_level_media_rights_and_context(image):
    assert MediaReference.model_validate(image).kind == "image"
    for updates in (
        {"asset_url": "https://publisher.test/image.jpg"},
        {"license_url": "https://publisher.test/"},
        {"creator": ""},
        {"title": "Unrelated Image"},
        {"license": "Unknown"},
    ):
        with pytest.raises(ValueError):
            MediaReference.model_validate(image | updates)
    # YouTube metadata and expiring platform assets cannot enter durable Git state.
    with pytest.raises(ValueError):
        MediaReference.model_validate(
            image | {"kind": "video", "source_url": "https://youtube.com/watch?v=fixture"}
        )


@pytest.mark.asyncio
async def test_signed_media_association_rejects_unrelated_headlines(release, signing, image):
    target = next(r for r in release.records if r.metadata.publisher == "Federal Reserve Board")
    raw = release.model_dump(mode="json")
    raw["media"] = [
        MediaLink(
            reference=MediaReference.model_validate(image), record_ids=(target.metadata.id,)
        ).model_dump(mode="json")
    ]
    with pytest.raises(ValueError, match="association"):
        parse_export(canonical(resign(raw, signing)))


@pytest.mark.asyncio
async def test_state_parent_sequence_and_concurrency(previous, release, monkeypatch):
    store = GitHubState()
    monkeypatch.setattr(store, "current", lambda: ("head", previous))
    with pytest.raises(StateError, match="parent"):
        store.prepare(release, "stale-head")
    monkeypatch.setattr(store, "head", lambda: "moved")
    with pytest.raises(StateError, match="concurrently"):
        store.commit({"dataset.json": b"{}"}, "head", "Fixture")
    with pytest.raises(StateError, match="allowlist"):
        store.commit({"private.key": b"secret"}, None, "Fixture")


@pytest.mark.asyncio
async def test_prepared_release_resumes_without_changing_current(
    previous, release, monkeypatch, tmp_path
):
    store = GitHubState()
    identity = daily.digest(release)
    monkeypatch.setattr(store, "current", lambda: ("head", previous))
    monkeypatch.setattr(
        store,
        "read",
        lambda *args: canonical({"release": identity, "parent": daily.digest(previous)}),
    )
    monkeypatch.setattr(store, "release", lambda *args: release)
    result = store.download(tmp_path / "previous.json", tmp_path / "candidate.json")
    assert result["resume"] == "true"
    assert daily.digest(parse_export((tmp_path / "previous.json").read_bytes())) == daily.digest(
        previous
    )
    assert daily.digest(parse_export((tmp_path / "candidate.json").read_bytes())) == identity
    with pytest.raises(StateError, match="state changed"):
        store.promote(identity, "stale-head")

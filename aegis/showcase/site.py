"""Reproducible, dependency-free static rendering and strict output inventory audit."""

# HTML templates below retain prose and attribute boundaries for reviewability.
# ruff: noqa: E501

import base64
import hashlib
import html
import json
import re
import shutil
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from aegis.provenance.service import canonical
from aegis.showcase.contracts import POLICY_URL, PublicExport, PublicRecord
from scripts.scan_secrets import violations

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps/showcase"
NAV = {
    "/": "Discover",
    "/archive/": "News Archive",
    "/topics/": "Topic Intelligence",
    "/evidence/": "Entity & Event Evidence",
    "/analytics/": "Analytics",
    "/media/": "Media References",
    "/verification/": "Cryptography",
}


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def outputs(record: PublicRecord, task: str) -> list[dict[str, Any]]:
    return [
        output.model_dump(mode="json")
        for analysis in record.analyses
        if analysis.analysis_type == task
        for output in analysis.outputs
    ]


def topic(record: PublicRecord) -> str:
    return str(outputs(record, "topic")[0]["label"])


def date(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%d %b %Y · %H:%M UTC")
    return e(value) if value else "Unknown"


def story_link(record: PublicRecord) -> str:
    return "/stories/" + record.metadata.id + "/"


def cards(records: list[PublicRecord]) -> str:
    return (
        '<div class="story-list">'
        + "".join(
            f'<article class="story" data-story data-topic="{e(topic(r))}" '
            f'data-search="{e(r.metadata.title.casefold())}">'
            f'<div class="story-meta">NASA <span>·</span> '
            f'<a href="/topics/{e(topic(r))}/">{e(topic(r).title())}</a></div>'
            f'<h2><a href="{story_link(r)}">{e(r.metadata.title)}</a></h2>'
            f'<div class="caption">Published {date(r.metadata.published_at)}</div>'
            f'<a class="source-link" href="{e(r.metadata.url)}" rel="noreferrer">'
            "Original NASA Reporting ↗</a></article>"
            for r in records
        )
        + "</div>"
    )


def intro(eyebrow: str, title: str, description: str) -> str:
    return (
        f'<div class="intro"><p class="eyebrow">{e(eyebrow)}</p><h1>{e(title)}</h1>'
        f'<p class="lede">{e(description)}</p></div>'
    )


def shell(dataset: PublicExport, route: str, title: str, body: str) -> str:
    navigation = "".join(
        f'<a href="{path}" {"aria-current=page" if route == path else ""}>{e(label)}</a>'
        for path, label in NAV.items()
    )
    digest = hashlib.sha256(canonical(dataset.model_dump(mode="json"))).hexdigest()
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Aegis News: a frozen, public news-intelligence collection with verifiable provenance.">
<meta name="aegis-public-key" content="{e(dataset.public_key)}">
<title>{e(title)} — Aegis News</title><link rel="stylesheet" href="/assets/style.css">
<script type="module" src="/assets/app.js"></script></head><body>
<a class="skip" href="#main">Skip To Content</a>
<header><a class="brand" href="/">Aegis<span>News</span><small>News Intelligence & Provenance</small></a>
<div class="edition"><span class="seal">Public Read-Only Edition</span><br>Frozen Collection · {len(dataset.records)} Records</div></header>
<nav aria-label="Primary">{navigation}</nav>
<div class="dateline">Dataset Updated {date(dataset.exported_at)}<a href="/data/manifest.json">Release {digest[:12]} ↗</a></div>
<main id="main">{body}</main>
<footer><div class="brand">Aegis<span>News</span></div><p>An Information Security & Cryptography Academic Project.</p>
<p>Publisher reporting and Aegis heuristic outputs are identified separately. A valid signature does not establish factual accuracy.</p>
<a href="/about/">Sources & Limitations</a> · <a href="/verification/">Verify Public Evidence</a> · <a href="/data/dataset.json">Download Public Dataset</a>
<p class="caption">No accounts. No public write operations. Data remains frozen until manually refreshed.</p></footer></body></html>"""


def pages(dataset: PublicExport) -> dict[str, tuple[str, str]]:
    records = sorted(
        dataset.records,
        key=lambda r: (r.metadata.published_at or r.metadata.acquired_at, r.metadata.id),
        reverse=True,
    )
    counts = Counter(topic(r) for r in records)
    lead = records[0]
    hero = (
        intro(
            "The Public Collection",
            "Reporting, With A Record.",
            "Explore original source reporting, headline intelligence and the evidence behind each published record.",
        )
        + '<div class="lead-grid"><section class="lead-story"><p class="eyebrow">From The Collection · NASA</p>'
        + f'<h2><a href="{story_link(lead)}">{e(lead.metadata.title)}</a></h2>'
        + f'<p class="caption">Published {date(lead.metadata.published_at)}</p>'
        + "<p>Read the original at NASA. Inspect Aegis’s headline-level analysis and verify its signed publication evidence.</p>"
        + f'<a class="button" href="{story_link(lead)}">Explore This Record →</a></section>'
        + '<aside class="evidence-rail"><p class="eyebrow">The Evidence Trail</p><ol>'
        + "<li><strong>Source Metadata</strong><span>Attributed headline, link and actual timestamps.</span></li>"
        + "<li><strong>Headline Intelligence</strong><span>Existing offline Aegis baselines, clearly labelled.</span></li>"
        + "<li><strong>Signed Public Bytes</strong><span>SHA-256 integrity and Ed25519 verification in your browser.</span></li></ol>"
        + '<a href="/verification/">How Verification Works →</a></aside></div>'
        + '<div class="section-heading"><h2>In The Archive</h2><a href="/archive/">View All Records →</a></div>'
        + cards(records[1:7])
    )
    search = (
        '<div class="search-controls"><label for="search">Search Headlines</label>'
        '<input id="search" type="search" placeholder="Search The Frozen Collection" autocomplete="off">'
        '<label for="topic">Topic</label><select id="topic"><option value="">All Topics</option>'
        + "".join(f'<option value="{e(t)}">{e(t.title())}</option>' for t in sorted(counts))
        + '</select></div><p id="search-status" role="status">'
        + str(len(records))
        + ' Records</p><p id="no-results" hidden>No Matching Headlines. Try Another Term Or Topic.</p>'
    )
    result = {
        "/": ("Discover", hero),
        "/archive/": (
            "News Archive",
            intro(
                "The Frozen Record",
                "News Archive & Search",
                "Search runs entirely in your browser. Records are ordered by publication time; unknown dates fall back to acquisition time.",
            )
            + search
            + cards(records),
        ),
        "/topics/": (
            "Topic Intelligence",
            intro(
                "Headline Intelligence",
                "Topic Intelligence",
                "Topics come from Aegis’s keyword baseline applied to the headline only. General means no specific topic matched.",
            )
            + '<div class="topic-grid">'
            + "".join(
                f'<a class="topic-card" href="/topics/{e(t)}/"><h2>{e(t.title())}</h2><span>{n} Records →</span></a>'
                for t, n in sorted(counts.items())
            )
            + "</div>",
        ),
    }
    for name in sorted(counts):
        result[f"/topics/{name}/"] = (
            name.title(),
            intro(
                "Topic Intelligence",
                name.title(),
                "Heuristic headline classification. Topic assignments are model outputs, not publisher labels.",
            )
            + cards([r for r in records if topic(r) == name]),
        )
    evidence = intro(
        "Linked To The Source",
        "Entity & Event Evidence",
        "Capitalized spans and keyword event candidates from headlines. These are unreviewed heuristic outputs; entity identities and event occurrence times are unknown.",
    )
    for r in records:
        mentions = outputs(r, "entity_extraction")
        events = outputs(r, "event_extraction")
        if mentions or events:
            evidence += f'<section class="evidence-entry"><h2><a href="{story_link(r)}">{e(r.metadata.title)}</a></h2>'
            evidence += "".join(
                f'<p><span class="tag">Entity Candidate</span> {e(m["surface"])} · '
                f"Headline Offsets {m['start_offset']}–{m['end_offset']} · "
                f"Confidence {m['confidence']:.0%} · Unresolved</p>"
                for m in mentions
            )
            evidence += "".join(
                f'<p><span class="tag">Event Candidate</span> {e(v["proposed_event_type"].title())} · '
                f"Confidence {v['confidence']:.0%}</p><blockquote>{e(v['evidence_text'])}</blockquote>"
                for v in events
            )
            evidence += "</section>"
    result["/evidence/"] = ("Entity & Event Evidence", evidence)
    sentiment = Counter(outputs(r, "sentiment")[0]["label"] for r in records)
    analytics = intro(
        "This Collection Only",
        "Intelligence Analytics",
        "Counts describe this curated NASA collection, not the wider news landscape. Sentiment is a headline lexicon baseline, not a claim about the event.",
    )
    analytics += f'<div class="metrics"><div><strong>{len(records)}</strong>Genuine Records</div><div><strong>1</strong>Publisher</div><div><strong>{len(counts)}</strong>Headline Topics</div><div><strong>{sum(r.metadata.published_at is None for r in records)}</strong>Unknown Publication Times</div></div>'
    for label, values in (("Topic Distribution", counts), ("Headline Sentiment", sentiment)):
        analytics += f'<section class="distribution"><h2>{label}</h2><table><caption>{label} · {len(records)} Records</caption><thead><tr><th scope="col">Label</th><th scope="col">Records</th><th scope="col">Share</th></tr></thead><tbody>'
        for name, count in sorted(values.items()):
            analytics += f'<tr><th scope="row">{e(str(name).title())}</th><td>{count}</td><td>{count / len(records):.1%}</td></tr>'
        analytics += "</tbody></table></section>"
    analytics += "<p>Each record contributes exactly once to each distribution. No synthetic records, inferred publication dates or hidden denominators.</p>"
    result["/analytics/"] = ("Intelligence Analytics", analytics)
    result["/media/"] = (
        "Media References",
        intro(
            "At The Original Source",
            "Media References",
            "Images, video and publisher bodies are not licensed into this public export. Follow NASA’s original pages to inspect media and its individual credits.",
        )
        + '<div class="notice">No Media Assets Published. NASA pages may include third-party material with separate rights. There is no public media authenticity claim.</div>'
        + cards(records),
    )
    result["/verification/"] = ("Cryptographic Evidence", cryptography(dataset))
    result["/about/"] = (
        "Sources & Limitations",
        intro(
            "A Deliberate Boundary",
            "Sources & Limitations",
            "An independently curated academic showcase. Aegis is not affiliated with or endorsed by NASA.",
        )
        + f'<section class="prose"><h2>Source & Rights</h2><p>NASA’s public RSS feed and public press-release API supply headline metadata, canonical source links and publication dates. Collection is manual. No publisher excerpts, article bodies, logos, photos or video are republished.</p><p><a href="{POLICY_URL}">NASA Usage Guidelines ↗</a>. Third-party material on NASA pages may have separate copyright. Source links carry attribution; no blanket third-party reuse rights are asserted. This metadata policy has no provider-imposed expiry; review terms before adding any new source.</p>'
        + "<h2>What The Intelligence Means</h2><p>The existing Aegis offline profile runs keyword topics, lexicon sentiment, capitalized-span candidates and keyword event candidates on headlines only. No generative summaries, trained-model inference, resolved entity identities or independently verified events are claimed. Missing findings remain absent.</p>"
        + "<h2>Private Application</h2><p>The secured local application retains full ingestion, archive encryption, access control, audit review and the complete tampering and restoration demonstration. None of those operations is exposed here.</p>"
        + "<h2>Frozen Publication</h2><p>Refresh requires an explicit local acquisition and signed export followed by a manual publication. This site never calls a provider or the private Aegis API. Unknown publication times remain unknown.</p></section>",
    )
    for record in records:
        m = record.metadata
        analysis = '<section class="prose"><h2>Aegis Headline Intelligence</h2><p class="notice">Heuristic Model Outputs · Offline Baselines · Headline Only · Unreviewed</p>'
        analysis += f'<p>Topic: <a href="/topics/{e(topic(record))}/">{e(topic(record).title())}</a>. Sentiment: {e(outputs(record, "sentiment")[0]["label"].title())}.</p>'
        mentions = outputs(record, "entity_extraction")
        events = outputs(record, "event_extraction")
        analysis += "<h3>Entity Candidates</h3>" + (
            "<ul>"
            + "".join(
                f"<li>{e(v['surface'])} · Confidence {v['confidence']:.0%} · Unresolved</li>"
                for v in mentions
            )
            + "</ul>"
            if mentions
            else "<p>No Entity Candidates Found In This Headline.</p>"
        )
        analysis += "<h3>Event Candidates</h3>" + (
            "".join(
                f"<p>{e(v['proposed_event_type'].title())} · Confidence {v['confidence']:.0%}</p><blockquote>{e(v['evidence_text'])}</blockquote>"
                for v in events
            )
            if events
            else "<p>No Event Candidates Found In This Headline.</p>"
        )
        analysis += (
            "<details><summary>Model Receipts & Confidence</summary>"
            + "".join(
                f"<p>{e(a.analysis_type)} · {e(a.model_name)} v{e(a.model_version)} · {e(a.provider)}</p><code>{e(a.configuration_hash)}</code><pre>{e(json.dumps([o.model_dump(mode='json') for o in a.outputs], ensure_ascii=False, indent=2))}</pre>"
                for a in record.analyses
            )
            + "</details></section>"
        )
        body = intro(
            "Source Record · NASA",
            m.title,
            "Original reporting is available at the publisher. This page publishes metadata and Aegis’s separate analysis.",
        )
        body += f'<a class="button" href="{e(m.url)}" rel="noreferrer">Read Original At NASA ↗</a><dl class="record-meta"><dt>Published</dt><dd>{date(m.published_at)}</dd><dt>Acquired</dt><dd>{date(m.acquired_at)}</dd><dt>Public Record ID</dt><dd><code>{m.id}</code></dd></dl>'
        body += (
            analysis
            + f'<section class="verification-panel"><h2>Verify This Public Record</h2><p>Checks the signed metadata, analysis bytes and hash chain. This is publication evidence, not a factual-accuracy rating.</p><button data-verify="{m.id}">Verify Signed Evidence</button><p role="status" class="verify-status">Ready To Verify In Your Browser.</p><a href="/data/evidence/{m.id}/manifest.json">Download Signed Manifest</a> · <a href="/verification/">Verification Explained</a></section>'
        )
        result[story_link(record)] = (m.title, body)
    result["/404/"] = (
        "Page Not Found",
        intro("404", "Page Not Found", "This route is not part of the public collection.")
        + '<a href="/archive/">Return To The Archive →</a>',
    )
    return result


def cryptography(dataset: PublicExport) -> str:
    fingerprint = hashlib.sha256(base64.b64decode(dataset.public_key)).hexdigest()
    return (
        intro(
            "Information Security & Cryptography",
            "Evidence You Can Inspect.",
            "The public edition exposes verifiable publication evidence. Protected archives and security operations stay in the private local application.",
        )
        + f'''
<div class="crypto-grid">
<section><p class="eyebrow">Integrity</p><h2>SHA-256</h2><p>Aegis hashes content bytes using SHA-256. Public records include hashes of canonical UTF-8 metadata and analysis bytes. Every lineage step also hashes the previous chain value and its record.</p></section>
<section><p class="eyebrow">Authenticity</p><h2>Ed25519 Provenance</h2><p>The existing ProvenanceService signs its canonical manifest body with Ed25519. Verification checks that signature, the complete lineage chain and every published content hash. This is Aegis provenance v1, not C2PA.</p></section>
<section><p class="eyebrow">Confidentiality · Private Stack</p><h2>AES-256-GCM</h2><p>The local archive encryption implementation requires a 32-byte AES key and a 96-bit nonce. Authenticated data binds the algorithm, key ID, version and caller context. The persistent nonce allocator prevents reuse. No archive ciphertext, decryption keys or protected plaintext is included here.</p></section>
<section><p class="eyebrow">Authorization · Private Stack</p><h2>Access Control</h2><p>The local API validates signed access tokens against configured issuer keys and checks scopes plus roles. Public browsing uses static files and has no token forms, administrator identity or write endpoint.</p></section>
<section><p class="eyebrow">Accountability · Private Stack</p><h2>Security Audit</h2><p>Aegis records allowlisted actions and outcomes, hashes actor and subject identities, and discards non-allowlisted audit fields. Internal administrative audit records stay private. Public releases identify their source commit and export digest.</p></section>
<section><p class="eyebrow">Verification</p><h2>Tamper Detection</h2><p>Changing metadata, analysis, lineage or signature bytes causes verification to fail. The private application retains the complete archive tampering and restoration demonstration. Public verification never writes or restores private data.</p></section></div>
<section class="verification-panel"><h2>Verify A Published Record</h2><p>Your browser uses Web Crypto to check SHA-256 and Ed25519 against the exact public bytes. Unsupported browsers report verification unavailable.</p>
<button data-verify="{dataset.records[0].metadata.id}">Verify Signed Evidence</button><p class="verify-status" role="status">Ready To Verify In Your Browser.</p>
<h3>Public Key Fingerprint · SHA-256</h3><code>{fingerprint}</code>
<p>The verification key is pinned in the reviewed repository’s trust.json. A site-supplied key alone cannot establish publisher identity: compare this fingerprint with a separately trusted copy. The export key is dedicated to this showcase; this does not assert verification of private archive bytes.</p>
<p><strong>A valid signature does not establish factual accuracy.</strong> It demonstrates consistency with the signer’s published bytes and key.</p></section>'''
    )


def artifact_bytes(dataset: PublicExport) -> dict[str, bytes]:
    artifacts = {}
    for route, (title, body) in pages(dataset).items():
        path = "404.html" if route == "/404/" else route.strip("/") + "/index.html"
        artifacts[path.lstrip("/")] = shell(dataset, route, title, body).encode()
    for name in ("style.css", "app.js"):
        artifacts["assets/" + name] = (APP / name).read_bytes()
    fonts = ROOT / "apps/web/src/app/fonts"
    for name in (
        "InterVariable.woff2",
        "SourceSerif4Variable-Roman.woff2",
        "Inter-LICENSE.txt",
        "SourceSerif-LICENSE.md",
    ):
        artifacts["assets/" + name] = (fonts / name).read_bytes()
    content = canonical(dataset.model_dump(mode="json"))
    digest = hashlib.sha256(content).hexdigest()
    artifacts["data/dataset.json"] = content
    artifacts["data/public-key.json"] = canonical(
        {"algorithm": "Ed25519", "key_id": dataset.key_id, "public_key": dataset.public_key}
    )
    for record in dataset.records:
        prefix = "data/evidence/" + record.metadata.id + "/"
        values = list(record.contents().values())
        artifacts[prefix + "metadata.json"] = values[0]
        artifacts[prefix + "analysis.json"] = values[1]
        artifacts[prefix + "manifest.json"] = canonical(record.provenance.model_dump(mode="json"))
        artifacts[prefix + "signed-body.json"] = canonical(
            record.provenance.model_dump(mode="json", exclude={"signature"})
        )
    artifacts["_headers"] = (APP / "_headers").read_bytes()
    artifacts["robots.txt"] = b"User-agent: *\nAllow: /\n"
    artifacts["data/manifest.json"] = canonical(
        {
            "version": "aegis-public-release-1",
            "export_sha256": digest,
            "exported_at": dataset.exported_at.isoformat(),
            "source_commit": dataset.source_commit,
            "records": len(dataset.records),
            "rights": dataset.policy,
            "files": {
                path: hashlib.sha256(value).hexdigest() for path, value in sorted(artifacts.items())
            },
        }
    )
    return artifacts


def check_trust(dataset: PublicExport) -> None:
    trust = json.loads((APP / "trust.json").read_bytes())
    if trust != {"key_id": dataset.key_id, "public_key": dataset.public_key}:
        raise ValueError("export key does not match reviewed publication trust anchor")


def build(dataset: PublicExport, output: Path) -> None:
    check_trust(dataset)
    # Only replace the named generated output, never an arbitrary user directory.
    if output.resolve() != (APP / "dist").resolve():
        raise ValueError("build output must be apps/showcase/dist")
    artifacts = artifact_bytes(dataset)
    if output.is_symlink():
        raise ValueError("output cannot be a symlink")
    if output.exists():
        shutil.rmtree(output)
    for name, content in artifacts.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    audit(dataset, output)


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.links.append(value)
        if tag in {"form", "iframe"} or any(k.startswith("on") for k, _ in attrs):
            raise ValueError("active form, frame or inline handler in output")


def audit(dataset: PublicExport, output: Path) -> None:
    check_trust(dataset)
    expected = artifact_bytes(dataset)
    paths = list(output.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("symlink in publication")
    actual = {p.relative_to(output).as_posix(): p.read_bytes() for p in paths if p.is_file()}
    if actual != expected:
        raise ValueError("static output differs from validated allowlisted build")
    if len(actual) > 20000 or any(len(v) > 25 * 1024 * 1024 for v in actual.values()):
        raise ValueError("Cloudflare Pages Free asset limits exceeded")
    forbidden = re.compile(
        rb"localhost|127\.0\.0\.1|/api/|localStorage|sessionStorage|WebSocket|EventSource"
    )
    for name, value in actual.items():
        if violations(name, value):
            raise ValueError("secret guard rejected artifact: " + name)
        if name.endswith((".html", ".js", ".json", ".css")) and forbidden.search(value):
            raise ValueError("private endpoint or credential persistence in artifact: " + name)
        if name.endswith(".html"):
            links = Links()
            links.feed(value.decode())
            for link in links.links:
                if link.startswith("/"):
                    target = urlsplit(link).path.lstrip("/")
                    target = target + "index.html" if target.endswith("/") or not target else target
                    if target not in actual:
                        raise ValueError("broken static link: " + link)
                elif not link.startswith(("https://", "#")):
                    raise ValueError("unsupported public reference")
    print(
        f"Static audit passed: {len(actual)} allowlisted files, {len(pages(dataset))} routes, {len(dataset.records)} signed records"
    )

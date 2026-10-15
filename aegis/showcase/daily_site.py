"""Editorial additions for signed multi-source releases; legacy evidence stays intact."""

# ruff: noqa: E501
import base64
import hashlib
from collections import Counter

from aegis.showcase.contracts import DailyExport
from aegis.showcase.daily_contracts import MetadataV2
from aegis.showcase.sources import REGISTRY


def enrich(dataset: DailyExport, pages: dict[str, tuple[str, str]]) -> None:
    from aegis.showcase.site import cards, date, e, intro

    records = list(dataset.records)
    by_id = {r.metadata.id: r for r in records}
    counts = Counter(m.reference.kind for m in dataset.media)
    media = intro(
        "Sources In Context",
        "Media Lab",
        "Original articles, licensed context images and official video references. Media bytes are not verified by Aegis.",
    )
    media += '<nav class="media-tabs" aria-label="Media Type"><a href="#articles">News Articles</a><a href="#images">Images</a><a href="#videos">Videos</a></nav>'
    for kind, heading in (("image", "Images"), ("video", "Videos")):
        values = [m for m in dataset.media if m.reference.kind == kind]
        media += f'<section id="{heading.lower()}"><div class="section-heading"><h2>{heading}</h2><span>{len(values)} References</span></div><div class="media-grid">'
        for item in values:
            m = item.reference
            visual = (
                f'<div class="media-image"><img src="{e(m.asset_url)}" alt="{e(m.alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer"><span class="image-fallback" hidden>Image Unavailable. Follow The Source Link Below.</span></div>'
                if m.asset_url
                else '<p class="video-mark" aria-hidden="true">↗</p>'
            )
            media += (
                f'<article class="media-entry">{visual}<p class="eyebrow">{e(m.publisher)} · Context Reference</p><h3><a href="{e(m.source_url)}" rel="noreferrer">{e(m.title)} ↗</a></h3><p>Creator: {e(m.creator)} · <a href="{e(m.license_url)}">{e(m.license)}</a></p><p class="caption">Related By “{e(m.relationship_term)}”; Not A Depiction Claim. Created {date(m.created_at)} · Published {date(m.published_at)} · Refreshed {date(m.refreshed_at)}.</p><details><summary>Associated Headlines</summary><ul>'
                + "".join(
                    f'<li><a href="/stories/{identity}/">{e(by_id[identity].metadata.title)}</a></li>'
                    for identity in item.record_ids
                )
                + "</ul></details></article>"
            )
        if not values:
            media += '<p class="notice">No Permitted References In This Release. Read The Original Sources For Available Media.</p>'
        media += "</div></section>"
    pages["/media/"] = (
        "Media Lab",
        media + '<section id="articles"><h2>News Articles</h2>' + cards(records) + "</section>",
    )
    title, analytics = pages["/analytics/"]
    published = [r.metadata.published_at for r in records if r.metadata.published_at]
    analytics += (
        f'<section class="prose"><h2>Population & Freshness</h2><p>Publication Range: {date(min(published)) if published else "Unknown"} — {date(max(published)) if published else "Unknown"}.</p><p>Latest Acquisition: {date(max(r.metadata.acquired_at for r in records))}. Release: {date(dataset.exported_at)}.</p><p>{counts["image"]} Image References · {counts["video"]} Video References.</p><h2>Publisher Coverage</h2><ul>'
        + "".join(
            f"<li>{e(name)} · {count} Records</li>"
            for name, count in sorted(Counter(r.metadata.publisher for r in records).items())
        )
        + "</ul><h2>Source Editorial Categories</h2><ul>"
        + "".join(
            f"<li>{e(name)} · {count} Records</li>"
            for name, count in sorted(
                Counter(
                    c for r in records for c in getattr(r.metadata, "source_categories", ())
                ).items()
            )
        )
        + "</ul><p>Categories May Overlap. Source Labels Do Not Change Model Topic Assignments.</p></section>"
    )
    pages["/analytics/"] = (title, analytics)
    rights = "".join(
        f'<li><strong>{e(p.name)}</strong> · Metadata And Source Links Only · <a href="{e(p.rights_url)}">Rights & Attribution ↗</a></li>'
        for p in REGISTRY.values()
    )
    pages["/about/"] = (
        "Sources & Limitations",
        intro(
            "A Deliberate Boundary",
            "Sources & Limitations",
            "An independent academic project. No source endorsement is implied.",
        )
        + '<section class="prose"><h2>Sources & Rights</h2><ul>'
        + rights
        + '</ul><p>Publisher bodies and excerpts are excluded. <a href="https://www.gdeltproject.org/">The GDELT Project</a> supplies discovery metadata, not rights to publisher articles or photographs.</p><h2>Selection & Freshness</h2><p>Candidates target 48 hours with bounded catch-up up to seven days. Permitted complete records are ordered by publication or provider discovery time, then selected round-robin across publishers: at most eight per publisher, 48 new records per run. No viral score, independent corroboration or universal coverage is claimed. Up to 300 records remain in a rolling 21-day archive. Unknown publication dates stay unknown.</p><h2>Media Rights</h2><p>Commons images require per-file rights metadata and creator attribution. Context references match an explicit headline term and do not claim to depict the reported event. NASA videos link to the official library, without downloaded videos, thumbnails or embedded players. Library creation dates are not publication dates. YouTube API metadata is excluded because its deletion obligations conflict with permanent Git history.</p><h2>Model Limits</h2><p>Existing offline keyword topics, lexicon sentiment, capitalized spans and keyword event candidates process headlines only. General remains an honest unmatched topic. Sentiment is not public opinion. Source editorial categories are separate from model predictions. No generated reporting, resolved identities or independently verified events are claimed.</p><h2>Publication & Private Boundaries</h2><p>Each update is a validated static release. The browser never calls news APIs. Failed or empty acquisition retains the previous valid release. The daily workflow requires approved default-branch integration and explicit activation. Encryption, authenticated ingestion, audit review and tamper restoration remain in the secured local application.</p></section>',
    )
    title, crypto = pages["/verification/"]
    crypto += (
        '<section class="verification-panel"><h2>Complete Release & Trust Registry</h2><p>The release signature binds membership, sequence, parent digest and media metadata. Compare the reviewed registry with a separately trusted repository copy.</p><button data-verify-release>Verify Complete Release</button><p class="release-status" role="status">Ready To Verify Release Membership And Media Metadata.</p><ul>'
        + "".join(
            f"<li><code>{e(key)}</code> · {e(entry.status)} · SHA-256 <code>{hashlib.sha256(base64.b64decode(entry.public_key)).hexdigest()}</code></li>"
            for key, entry in dataset.trust.keys.items()
        )
        + "</ul><p>A Valid Signature Does Not Establish Factual Accuracy Or Authenticate External Media Bytes.</p></section>"
    )
    pages["/verification/"] = (
        title,
        crypto.replace(
            "repository’s trust.json",
            "repository’s trust-registry.json (daily) and trust.json (legacy)",
        ),
    )
    for r in records:
        route = "/stories/" + r.metadata.id + "/"
        title, body = pages[route]
        metadata = r.metadata
        if isinstance(metadata, MetadataV2):
            body += f'<section class="prose"><h2>Source Timestamps & Categories</h2><p>Provider Discovery: {date(metadata.discovered_at)} · Source Updated: {date(metadata.source_updated_at)} · Event Occurrence: {date(metadata.occurred_at)}.</p><p>Source Categories: {e(", ".join(metadata.source_categories) or "Unknown")}. These Are Not Model Predictions.</p></section>'
        related = [m for m in dataset.media if r.metadata.id in m.record_ids]
        if related:
            body += (
                '<section class="prose"><h2>Context Media</h2><p>Related By Headline Terms; Not Evidence Of This Event.</p><ul>'
                + "".join(
                    f'<li><a href="{e(m.reference.source_url)}">{e(m.reference.title)} ↗</a> · {e(m.reference.publisher)}</li>'
                    for m in related
                )
                + "</ul></section>"
            )
        pages[route] = (title, body)

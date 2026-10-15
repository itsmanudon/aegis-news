"""Reviewed acquisition/publication policy. No endpoint is supplied by news content."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from aegis.providers.models import safe_url


@dataclass(frozen=True)
class SourcePolicy:
    name: str
    endpoint: str
    hosts: tuple[str, ...]
    rights_url: str
    coverage: str
    limit: int = 16
    kind: str = "rss"


REGISTRY = {
    "nasa": SourcePolicy(
        "NASA",
        "https://www.nasa.gov/feed/",
        ("www.nasa.gov", "science.nasa.gov"),
        "https://www.nasa.gov/nasa-brand-center/images-and-media/",
        "Science",
    ),
    "federal-reserve": SourcePolicy(
        "Federal Reserve Board",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        ("www.federalreserve.gov",),
        "https://www.federalreserve.gov/disclaimer.htm",
        "Business",
    ),
    "nist": SourcePolicy(
        "NIST",
        "https://www.nist.gov/news-events/news/rss.xml",
        ("www.nist.gov",),
        "https://www.nist.gov/copyrights-disclaimers",
        "Technology",
    ),
    "noaa": SourcePolicy(
        "NOAA Ocean Service",
        "https://oceanservice.noaa.gov/rss/nosnews.xml",
        ("oceanservice.noaa.gov",),
        "https://www.noaa.gov/disclaimer",
        "Environment",
    ),
    "usgs": SourcePolicy(
        "USGS Earthquake Hazards Program",
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
        ("earthquake.usgs.gov",),
        "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
        "Environment",
        kind="usgs",
    ),
    "gdelt": SourcePolicy(
        "The GDELT Project",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        (),
        "https://www.gdeltproject.org/about.html#termsofuse",
        "World",
        limit=30,
        kind="gdelt",
    ),
}
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
NASA_MEDIA_API = "https://images-api.nasa.gov/search"
MEDIA_ENDPOINTS = (COMMONS_API, NASA_MEDIA_API)


def approved_link(source: str, value: str) -> bool:
    policy = REGISTRY.get(source)
    return bool(
        policy
        and safe_url(value) == value
        and (not policy.hosts or urlsplit(value).hostname in policy.hosts)
    )

"""Conservative text normalization; unknown language and publisher time remain null."""

import json
from html.parser import HTMLParser

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from aegis.domain.models import NonEmpty


class Article(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: NonEmpty
    text: str = Field(min_length=1)
    language: str | None = Field(default=None, min_length=2, max_length=35)
    published_at: AwareDatetime | None = None

    @field_validator("title", "text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not value or "\x00" in value:
            raise ValueError("empty or binary article field")
        return value


class ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.parts: list[str] = []
        self.in_title = False
        self.hidden = 0
        self.language: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript"):
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        if tag == "html":
            self.language = dict(attrs).get("lang") or None
        if tag in ("p", "div", "br", "article", "h1", "h2", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False
        if tag in ("p", "div", "article", "h1", "h2", "li"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            (self.title_parts if self.in_title else self.parts).append(data)


def parse_article(content: bytes, content_type: str) -> Article:
    text = content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if "\x00" in text or not text.strip():
        raise ValueError("empty or binary article")
    if content_type == "application/json":
        return Article.model_validate(json.loads(text))
    if content_type == "text/html":
        parser = ArticleHTMLParser()
        parser.feed(text)
        parser.close()
        body = "\n".join(
            " ".join(line.split()) for line in "".join(parser.parts).splitlines() if line.strip()
        )
        title = " ".join("".join(parser.title_parts).split()) or body.split("\n")[0][:512]
        return Article(title=title, text=body, language=parser.language)
    if content_type != "text/plain":
        raise ValueError("unsupported article MIME")
    text = text.strip()
    return Article(title=text.split("\n")[0][:512], text=text)

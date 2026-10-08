import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { components } from "@/lib/generated/api";
import { documents } from "@/lib/fixtures";
import { Providers } from "../providers";
import {
  ArticleReference,
  MediaLabPage,
  StoredMediaRecords,
  VideoReference,
} from "./media-lab";

type Api = components["schemas"];
const article: Api["ProviderArticleView"] = {
  article_id: "article-demo",
  source_id: "source-demo",
  title: "Synthetic harbour report",
  document_id: "document-demo",
  acquired_at: "2026-10-08T08:10:07.125Z",
  published_at: null,
  evidence: [
    {
      provider: "gnews",
      publisher_name: "Example Daily",
      content_kind: "provider excerpt",
      acquired_at: "2026-10-08T08:05:00Z",
      article_url: "javascript:alert(1)",
      image_url: "https://127.0.0.1/private",
    },
    {
      provider: "newsapi",
      publisher_name: "Example Maritime",
      author: "Demo correspondent",
      content_kind: "headline only",
      acquired_at: "2026-10-08T08:09:00Z",
      provider_item_id: "reference-2",
      article_url: "https://publisher.example.org/story",
      image_url: "https://images.example.org/harbour.jpg",
    },
  ],
};
const video: Api["YouTubeReference"] = {
  video_id: "abcdefghijk",
  title: "Synthetic cargo briefing",
  channel_id: "channel-demo",
  channel_title: "Example Channel",
  youtube_url: "https://evil.example.org/watch",
  thumbnail_url: "https://images.example.org/video.jpg",
  published_at: "2026-10-07T12:01:00Z",
  last_refreshed_at: "2026-10-08T08:11:07.125Z",
  expires_at: "2026-11-07T08:11:07.125Z",
};

describe("Media Lab evidence presentation", () => {
  it("attributes the displayed remote image to its actual publisher and preserves every acquisition record", () => {
    const html = renderToStaticMarkup(<ArticleReference article={article} />);
    expect(html).toContain('src="https://images.example.org/harbour.jpg"');
    expect(html).toContain("Example Maritime · newsapi");
    expect(html).toContain("Example Daily");
    expect(html).toContain("Demo correspondent");
    expect(html).toContain("reference-2");
    for (const time of [
      "2026-10-08T08:05:00.000Z",
      "2026-10-08T08:09:00.000Z",
      "2026-10-08T08:10:07.125Z",
    ])
      expect(html).toContain(time);
    expect(html).toContain("Unknown");
    expect(html).toContain('href="/documents/document-demo"');
    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("127.0.0.1");
    expect(html).toContain('loading="lazy"');
    expect(html).toContain('referrerPolicy="no-referrer"');
    expect(html).toContain("not stored or cryptographically verified");
  });

  it("preserves publication, refresh and expiry independently and constructs a validated official video link", () => {
    const html = renderToStaticMarkup(<VideoReference video={video} />);
    for (const time of [
      "2026-10-07T12:01:00.000Z",
      "2026-10-08T08:11:07.125Z",
      "2026-11-07T08:11:07.125Z",
    ])
      expect(html).toContain(time);
    expect(html).toContain(
      'href="https://www.youtube.com/watch?v=abcdefghijk"',
    );
    expect(html).not.toContain("evil.example.org");
    expect(html).not.toContain("<iframe");
    expect(html).not.toContain("<video");
    expect(html).toContain("metadata only");
    expect(html).toContain("Example Channel");
  });

  it("withholds invalid video navigation and unsafe thumbnails without treating missing publication as refresh time", () => {
    const html = renderToStaticMarkup(
      <VideoReference
        video={{
          ...video,
          video_id: "bad/id",
          thumbnail_url: "https://host.local/image",
          published_at: null,
        }}
      />,
    );
    expect(html).not.toContain("href=");
    expect(html).not.toContain("<img");
    expect(html).toContain("Image Unavailable");
    expect(html).toContain("Unknown");
  });

  it("shows actual stored attachment metadata without claiming document provenance covers media bytes", () => {
    const html = renderToStaticMarkup(
      <StoredMediaRecords view={documents[2]} simulated />,
    );
    expect(html).toContain("corridor-report.txt");
    expect(html).toContain("text/plain");
    expect(html).toContain("2,048 bytes");
    expect(html).toContain("c".repeat(64));
    expect(html).toContain("fixture-evidence");
    expect(html).toContain("Fictional Demo Record");
    expect(html).toContain(
      "No provenance record in this response directly references this media asset.",
    );
    expect(html).toContain("Story Provenance");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("download=");
  });

  it("retains provenance records that explicitly name the media asset as subject or input", () => {
    const view = documents[2];
    const html = renderToStaticMarkup(
      <StoredMediaRecords
        view={{
          ...view,
          provenance: [
            {
              ...view.provenance[0],
              subject_id: view.media[0].media_id,
              operation: "capture-media",
            },
          ],
        }}
        simulated={false}
      />,
    );
    expect(html).toContain("capture-media");
    expect(html).toContain(view.provenance[0].content_hash);
    expect(html).not.toContain(
      "No provenance record in this response directly references this media asset.",
    );
    expect(html).toContain("No media integrity check has been run");
  });

  it("keeps mock provider capability unavailable and requires explicit story selection", () => {
    const html = renderToStaticMarkup(
      <Providers>
        <MediaLabPage />
      </Providers>,
    );
    expect(html).toContain("Media Lab");
    expect(html).toContain("Publisher References Unavailable");
    expect(html).toContain("Video References Unavailable");
    expect(html).toContain(
      "Select a story to inspect its stored attachment records.",
    );
    expect(html).not.toContain("corridor-report.txt");
  });
});

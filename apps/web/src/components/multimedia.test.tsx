import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { RemoteImage, safeExternalUrl, VideoCard } from "./multimedia";

describe("external multimedia", () => {
  it("rejects credentials, script URLs, local addresses and malformed numeric hosts", () => {
    for (const url of [
      "javascript:alert(1)",
      "http://example.org/a.jpg",
      "https://user:secret@example.org",
      "https://127.0.0.1/a",
      "https://127.01.0.1/a",
      "https://host.local/a",
      "https://example.org/a?api_key=secret",
    ])
      expect(safeExternalUrl(url)).toBeUndefined();
    expect(safeExternalUrl("https://images.example.org/news.jpg")).toBe(
      "https://images.example.org/news.jpg",
    );
  });
  it("uses a fallback for unsafe images without a fetch proxy", () => {
    const html = renderToStaticMarkup(
      <RemoteImage url="https://127.0.0.1/private" alt="News" />,
    );
    expect(html).toContain("Image unavailable");
    expect(html).not.toContain("<img");
  });
  it("labels YouTube references and links to the official watch page without autoplay", () => {
    const html = renderToStaticMarkup(
      <VideoCard
        video={{
          video_id: "abcdefghijk",
          title: "Synthetic technology report",
          channel_id: "channel",
          channel_title: "Example channel",
          youtube_url: "https://www.youtube.com/watch?v=abcdefghijk",
          last_refreshed_at: "2026-10-04T00:00:00Z",
          expires_at: "2026-11-02T00:00:00Z",
        }}
      />,
    );
    expect(html).toContain("Open on YouTube");
    expect(html).toContain("Video reference");
    expect(html).toContain("Example channel");
    expect(html).not.toContain("autoplay");
    expect(html).not.toContain("iframe");
  });
});

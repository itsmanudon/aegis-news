import type { DocumentView } from "./models";
export function assessmentLabel(type: string) {
  const labels: Record<string, string> = {
    topic: "Topic",
    sentiment: "Sentiment",
    entity_extraction: "Entity Extraction",
    entity_resolution: "Entity Resolution",
    event_extraction: "Event Extraction",
    event_classification: "Event Classification",
    embedding: "Embedding",
  };
  return labels[type] ?? type;
}
export function contentExtent(
  view: DocumentView,
  acquisition = view.acquisition ?? [],
) {
  const text = view.document.text.replace(/\s+/g, " ").trim();
  if (!text) return "No Source Text";
  if (text === view.document.title.replace(/\s+/g, " ").trim())
    return "Headline Only";
  if (acquisition.some((item) => item.content_kind === "provider excerpt"))
    return "Provider Excerpt";
  if (
    acquisition.length &&
    acquisition.every((item) => item.content_kind === "headline only")
  )
    return "Provider-Reported Headline Only";
  return "Captured Text · Extent Unconfirmed";
}
export function literalExcerpt(text: string, length = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  const characters = Array.from(normalized);
  if (characters.length <= length) return normalized;
  const preview = characters.slice(0, length).join("");
  const lastSpace = preview.lastIndexOf(" ");
  return `${preview.slice(0, lastSpace > 0 ? lastSpace : preview.length)}…`;
}
export function extractionSpan(
  text: string,
  start: number,
  end: number,
  surface: string,
) {
  const characters = Array.from(text);
  if (
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 0 ||
    end <= start ||
    end > characters.length
  )
    return;
  const span = characters.slice(start, end).join("");
  return span === surface ? span : undefined;
}

import type { components } from "./generated/api";
type Api = components["schemas"];
export type ArticleDraft = { title: string; text: string; key: string };
export class FormIssue extends Error {
  constructor(
    message: string,
    public field: string,
  ) {
    super(message);
  }
}
export function ingestionItems(
  sourceId: string,
  drafts: ArticleDraft[],
): Api["IngestionRequest"][] {
  if (!sourceId.trim())
    throw new FormIssue("Select a source before submitting.", "source");
  if (!drafts.length || drafts.length > 20)
    throw new FormIssue("Submit 1–20 articles per batch.", "batch");
  const keys = new Set<string>();
  const items = drafts.map((draft, index) => {
    for (const [field, value, label] of [
      ["title", draft.title, "Article Title"],
      ["text", draft.text, "Article Text"],
      ["key", draft.key, "Submission Key"],
    ]) {
      if (!value.trim())
        throw new FormIssue(`${label} must contain text.`, `${index}.${field}`);
    }
    if (draft.title.length > 512)
      throw new FormIssue(
        "Article Title must be at most 512 characters.",
        `${index}.title`,
      );
    if (draft.key.length > 512)
      throw new FormIssue(
        "Submission Key must be at most 512 characters.",
        `${index}.key`,
      );
    if (keys.has(draft.key))
      throw new FormIssue(
        "Use a distinct submission key for each article in this batch.",
        `${index}.key`,
      );
    keys.add(draft.key);
    const bytes = new TextEncoder().encode(draft.text);
    if (bytes.length > 256 * 1024)
      throw new FormIssue(
        "Article Text must fit within 256 KiB of UTF-8 content.",
        `${index}.text`,
      );
    const content = btoa(
      Array.from(bytes, (b) => String.fromCharCode(b)).join(""),
    );
    return {
      source_id: sourceId,
      title: draft.title.trim(),
      content_type: "text/plain" as const,
      content_base64: content,
      media: [],
      language: "en",
      idempotency_key: draft.key,
      correlation_id: crypto.randomUUID(),
    };
  });
  if (new TextEncoder().encode(JSON.stringify({ items })).length > 768 * 1024)
    throw new FormIssue(
      "The encoded batch must fit within the 768 KiB request limit. Reduce the batch before retrying.",
      "batch",
    );
  return items;
}
export function workflowState(status: unknown): string {
  if (
    typeof status !== "string" ||
    !status ||
    status === "UNKNOWN" ||
    status === "UNAVAILABLE"
  )
    return "Workflow State Unavailable";
  return (
    (
      {
        STARTED: "Workflow Started",
        RUNNING: "Workflow Running",
        COMPLETED: "Workflow Completed",
        FAILED: "Workflow Failed",
      } as Record<string, string>
    )[status] ?? status
  );
}
export function providerConfiguration(
  provider?: Api["ProviderStatus"],
): string {
  if (!provider) return "Provider Status Unknown";
  if (provider.provider === "gdelt")
    return provider.enabled
      ? "Keyless Capability Available"
      : "Capability Unavailable";
  return provider.enabled ? "Configuration Present" : "Configuration Missing";
}
export function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}
// Display-only source references. No fetch, proxy or media trust is implied.
export function sourceAddress(value?: string | null): string | undefined {
  if (!value || value.length > 4096 || /[\x00-\x20]/.test(value)) return;
  try {
    const url = new URL(value);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password
    )
      return;
    for (const key of url.searchParams.keys())
      if (/^(apikey|api_key|access_token|key|token)$/i.test(key)) return;
    return url.href;
  } catch {
    return;
  }
}

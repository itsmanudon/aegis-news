import { describe, expect, it } from "vitest";
import {
  ingestionItems,
  workflowState,
  providerConfiguration,
  sourceAddress,
} from "./operations";

describe("operational evidence presentation", () => {
  it("allows supported HTTP source references without exposing credentials or token parameters", () => {
    expect(sourceAddress("http://example.test/feed")).toBe(
      "http://example.test/feed",
    );
    expect(
      sourceAddress("https://user:secret@example.test/feed"),
    ).toBeUndefined();
    expect(
      sourceAddress("https://example.test/feed?api_key=secret"),
    ).toBeUndefined();
    expect(sourceAddress("javascript:alert(1)")).toBeUndefined();
  });
  it("never infers workflow completion from acceptance or missing status", () => {
    expect(workflowState(undefined)).toBe("Workflow State Unavailable");
    expect(workflowState("STARTED")).toBe("Workflow Started");
    expect(workflowState("RUNNING")).toBe("Workflow Running");
    expect(workflowState("COMPLETED")).toBe("Workflow Completed");
    expect(workflowState("FAILED")).toBe("Workflow Failed");
    expect(workflowState("UNKNOWN")).toBe("Workflow State Unavailable");
    expect(workflowState("TIMED_OUT")).toBe("TIMED_OUT");
  });
  it("distinguishes provider configuration from availability and credential health", () => {
    expect(
      providerConfiguration({
        provider: "gnews",
        enabled: true,
        mode: "manual",
      }),
    ).toBe("Configuration Present");
    expect(
      providerConfiguration({
        provider: "gnews",
        enabled: false,
        mode: "manual",
      }),
    ).toBe("Configuration Missing");
    expect(
      providerConfiguration({
        provider: "gdelt",
        enabled: true,
        mode: "manual",
      }),
    ).toBe("Keyless Capability Available");
    expect(providerConfiguration(undefined)).toBe("Provider Status Unknown");
  });
  it("encodes UTF8 text and preserves idempotency keys without substituting correlation IDs", () => {
    const items = ingestionItems("src-known", [
      { title: "Report", text: "Résumé 港", key: "same-key" },
    ]);
    expect(
      new TextDecoder().decode(
        Uint8Array.from(atob(items[0].content_base64), (c) => c.charCodeAt(0)),
      ),
    ).toBe("Résumé 港");
    expect(items[0].idempotency_key).toBe("same-key");
    expect(items[0].correlation_id).not.toBe("same-key");
    expect(items[0].media).toEqual([]);
  });
  it("rejects blank fields, duplicate batch keys, content and aggregate byte bounds", () => {
    const article = { title: "Report", text: "Evidence", key: "stable-key" };
    expect(() => ingestionItems("", [article])).toThrow("Select a source");
    expect(() =>
      ingestionItems("src-known", [{ ...article, title: "   " }]),
    ).toThrow("Article Title");
    expect(() =>
      ingestionItems("src-known", [{ ...article, text: "港".repeat(90000) }]),
    ).toThrow("256 KiB");
    expect(() => ingestionItems("src-known", [article, article])).toThrow(
      "distinct submission key",
    );
    expect(() =>
      ingestionItems(
        "src-known",
        Array.from({ length: 21 }, (_, i) => ({ ...article, key: String(i) })),
      ),
    ).toThrow("1–20");
    expect(() =>
      ingestionItems(
        "src-known",
        Array.from({ length: 4 }, (_, i) => ({
          ...article,
          key: String(i),
          text: "a".repeat(200000),
        })),
      ),
    ).toThrow("768 KiB");
  });
  it("identifies an oversized key as the key field rather than the title", () => {
    try {
      ingestionItems("src-known", [
        { title: "Short Title", text: "Evidence", key: "x".repeat(513) },
      ]);
      throw new Error("Expected validation failure");
    } catch (error) {
      expect(error).toHaveProperty("field", "0.key");
    }
  });
});

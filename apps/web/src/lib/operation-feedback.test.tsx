import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ApiClientError } from "./api";
import { OperationError } from "../components/operations/operation-feedback";
it("separates transport uncertainty from definitive authorization rejection", () => {
  for (const error of [
    new ApiClientError(
      "NETWORK_ERROR",
      "The API request timed out. Retry or check the connection.",
    ),
    new ApiClientError(
      "SOURCE_UNAVAILABLE",
      "Response unavailable",
      "uncertain-request",
      503,
    ),
  ]) {
    const html = renderToStaticMarkup(
      <OperationError error={error} write="source" />,
    );
    expect(html).toContain("Request Outcome Unknown");
    expect(html).not.toContain("Retry or check the connection");
    expect(html).toContain("Inspect the registry before retrying");
  }
  const denied = renderToStaticMarkup(
    <OperationError
      error={new ApiClientError("FORBIDDEN", "Scope revoked", "denied", 403)}
      write="provider"
    />,
  );
  expect(denied).toContain("Request Failed");
  expect(denied).not.toContain("Request Outcome Unknown");
  expect(denied).toContain("denied");
});

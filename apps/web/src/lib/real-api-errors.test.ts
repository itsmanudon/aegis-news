import { expect, it } from "vitest";
import { ApiClientError } from "./api";
import { realApiFailure } from "./real-api-errors";

it("explains missing, expired and forbidden Real API access without using mock data", () => {
  const missing = realApiFailure(
    new ApiClientError("UNAUTHORIZED", "Unauthorized", "req-1", 401),
  );
  expect(missing.title).toBe("Authorization Required");
  expect(missing.detail).toContain("python scripts/demo.py token --role analyst");
  expect(missing.detail).not.toContain("mock");

  const forbidden = realApiFailure(
    new ApiClientError("FORBIDDEN", "Forbidden", "req-2", 403),
  );
  expect(forbidden.title).toBe("Insufficient Scope");

  const offline = realApiFailure(
    new ApiClientError(
      "NETWORK_ERROR",
      "Unable to reach the API. Check the API address and connection.",
    ),
  );
  expect(offline.title).toBe("API Unreachable");
  expect(offline.detail).toContain("does not fall back to mock records");
});

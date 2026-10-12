import { expect, it } from "vitest";
import { ApiClientError } from "./api";
import { realApiFailure } from "./real-api-errors";

it("explains missing, expired and forbidden Real API access without using mock data", () => {
  const missing = realApiFailure(
    new ApiClientError("UNAUTHORIZED", "Unauthorized", "req-1", 401),
  );
  expect(missing.title).toBe("Authorization Required");
  expect(missing.detail).toBe("Unauthorized");
  expect(missing.guidance).toContain("python scripts/demo.py token --role analyst");
  expect(missing.guidance).not.toContain("mock");

  const forbidden = realApiFailure(
    new ApiClientError("FORBIDDEN", "Topic read scope required", "req-2", 403),
  );
  expect(forbidden.title).toBe("Insufficient Scope");
  expect(forbidden.detail).toBe("Topic read scope required");

  const offline = realApiFailure(
    new ApiClientError(
      "NETWORK_ERROR",
      "Unable to reach the API. Check the API address and connection.",
    ),
  );
  expect(offline.title).toBe("API Unreachable");
  expect(offline.detail).toContain("Unable to reach the API");
  expect(offline.guidance).toContain("does not fall back to mock records");
});

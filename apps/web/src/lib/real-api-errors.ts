import { ApiClientError } from "./api";

export function realApiFailure(error: Error): { title: string; detail: string } {
  if (error instanceof ApiClientError) {
    if (error.code === "UNAUTHORIZED" || error.status === 401) {
      return {
        title: "Authorization Required",
        detail:
          "This Real API request needs a fresh local development token. Generate one with python scripts/demo.py token --role analyst, paste it, and choose Use Token. Tokens expire after five minutes and stay in memory.",
      };
    }
    if (error.code === "FORBIDDEN" || error.status === 403) {
      return {
        title: "Insufficient Scope",
        detail:
          "This identity cannot perform the action. Generate a token for a role that includes the required scope. Admin can change sources; analyst and viewer cannot.",
      };
    }
    if (error.code === "NETWORK_ERROR") {
      return {
        title: "API Unreachable",
        detail:
          error.message +
          " Confirm the local API is running. Real API mode does not fall back to mock records.",
      };
    }
  }
  if (error instanceof ApiClientError && error.code === "CAPABILITY_UNAVAILABLE") {
    return { title: "Integration Pending", detail: error.message };
  }
  return { title: "Unable to Load Records", detail: error.message };
}

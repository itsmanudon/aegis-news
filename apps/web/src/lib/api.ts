// Only NEXT_PUBLIC_* configuration can be exposed to browser code.
export const publicApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const serverApiUrl = process.env.AEGIS_API_INTERNAL_URL ?? publicApiUrl;

export type SystemInfo = {
  name: "AegisNews";
  version: string;
  stage: "foundation";
  architecture: string;
};
export type ResponseMeta = { request_id: string; api_version: "v1" };
export type SingleResponse<T> = { data: T; meta: ResponseMeta };

export async function getSystemInfo(): Promise<SingleResponse<SystemInfo> | null> {
  try {
    const response = await fetch(`${serverApiUrl}/api/v1/system/info`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) return null;
    const value: unknown = await response.json();
    if (typeof value !== "object" || value === null || !("data" in value) || !("meta" in value)) return null;
    const { data, meta } = value;
    if (typeof data !== "object" || data === null || !("name" in data) || data.name !== "AegisNews" || !("version" in data) || typeof data.version !== "string" || !("stage" in data) || data.stage !== "foundation" || !("architecture" in data) || typeof data.architecture !== "string") return null;
    if (typeof meta !== "object" || meta === null || !("request_id" in meta) || typeof meta.request_id !== "string" || !("api_version" in meta) || meta.api_version !== "v1") return null;
    return value as SingleResponse<SystemInfo>;
  } catch {
    return null;
  }
}

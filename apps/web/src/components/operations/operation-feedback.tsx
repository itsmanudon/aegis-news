import { ApiClientError } from "@/lib/api";
import styles from "./operations.module.css";
export function OperationError({
  error,
  write,
}: {
  error: Error | null;
  write?: "source" | "ingestion" | "provider";
}) {
  if (!error) return null;
  const uncertain =
    !!write &&
    error instanceof ApiClientError &&
    (error.code === "NETWORK_ERROR" || (error.status ?? 0) >= 500);
  return (
    <div role="alert" className={styles.error}>
      <strong>
        {uncertain ? "Request Outcome Unknown" : "Request Failed"}
      </strong>
      <p>
        {uncertain
          ? "A confirmed response was not received. The operation may already have been accepted."
          : error.message}
      </p>
      {uncertain && (
        <p>
          {write === "source"
            ? "Inspect the registry before retrying. Repeating source creation can register a duplicate."
            : write === "provider"
              ? "Acquisition may already have started. Inspect a known provider run before submitting another request; repeating acquisition can consume additional quota."
              : "Preserve the source, article content and submission keys. Retry only the unchanged request to retain its idempotent workflow identity."}
        </p>
      )}
      {error instanceof ApiClientError && (
        <p className={styles.technical}>
          {error.code}
          {error.requestId ? ` · Request ${error.requestId}` : ""}
        </p>
      )}
    </div>
  );
}

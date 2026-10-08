import { ApiClientError } from "@/lib/api";
import styles from "./operations.module.css";
export function OperationError({ error }: { error: Error | null }) {
  if (!error) return null;
  return (
    <div role="alert" className={styles.error}>
      <strong>Request Failed</strong>
      <p>{error.message}</p>
      {error instanceof ApiClientError && (
        <p className={styles.technical}>
          {error.code}
          {error.requestId ? ` · Request ${error.requestId}` : ""}
        </p>
      )}
    </div>
  );
}

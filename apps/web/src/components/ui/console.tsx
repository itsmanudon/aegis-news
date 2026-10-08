import type { ButtonHTMLAttributes } from "react";
import { ApiClientError } from "@/lib/api";
export function Button({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`button ${className}`} {...props} />;
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  const statuses: Record<string, string> = {
    verified: "Verified",
    failed: "Failed",
    unverified: "Unverified",
    unavailable: "Unavailable",
    allowed: "Allowed",
    denied: "Denied",
    warning: "Warning",
  };
  return (
    <span className={`badge ${tone}`}>
      {typeof children === "string"
        ? (statuses[children] ?? children)
        : children}
    </span>
  );
}
export function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
export function PageHeading({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">Intelligence Operations</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Empty({
  message = "No records match these filters. Adjust the filters and try again.",
}: {
  message?: string;
}) {
  return (
    <p className="empty" role="status">
      {message}
    </p>
  );
}
export function QueryState({
  pending,
  error,
  retry,
  children,
}: {
  pending: boolean;
  error: Error | null;
  retry: () => unknown;
  children: React.ReactNode;
}) {
  if (pending)
    return (
      <div className="loading" role="status" aria-live="polite">
        <span className="loading-bar" />
        Loading intelligence records…
      </div>
    );
  if (error)
    return (
      <div className="error-state" role="alert">
        <h2>
          {error instanceof ApiClientError &&
          error.code === "CAPABILITY_UNAVAILABLE"
            ? "Integration Pending"
            : "Unable to Load Records"}
        </h2>
        <p>{error.message}</p>
        {error instanceof ApiClientError && (
          <p className="utility">
            {error.code}
            {error.requestId ? ` · Request ${error.requestId}` : ""}
          </p>
        )}
        <Button onClick={retry}>Retry</Button>
      </div>
    );
  return children;
}

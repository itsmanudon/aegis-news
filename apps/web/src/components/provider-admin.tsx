"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@/lib/generated/api";
import { providerConfiguration, workflowState } from "@/lib/operations";
import { useConsole } from "./providers";
import { Button, Empty, QueryState } from "./ui/console";
import { EvidenceDisclosure } from "./ui/evidence-disclosure";
import { Timestamp } from "./documents/time-rail";
import { useOperation } from "./operations/use-operation";
import { OperationError } from "./operations/operation-feedback";
import styles from "./operations/operations.module.css";
type Api = components["schemas"];
export function ProviderAdmin() {
  const { adapter, mode, session } = useConsole(),
    client = useQueryClient(),
    operation = useOperation();
  const permitted =
    mode === "real" &&
    !!session?.scopes?.includes("sources:write") &&
    !!session?.scopes?.includes("ingestions:write");
  const [run, setRun] = useState<Api["ProviderRun"]>(),
    [lookup, setLookup] = useState("");
  const [action, setAction] = useState<"acquire" | "lookup">("acquire"),
    [issue, setIssue] = useState("");
  const providers = useQuery({
    queryKey: [mode, "providers"],
    queryFn: ({ signal }) => adapter.providers!(signal),
    enabled: permitted && !!adapter.providers,
  });
  async function perform(
    work: (signal: AbortSignal) => Promise<Api["ProviderRun"]>,
    kind: "acquire" | "lookup",
  ) {
    if (!permitted || operation.busy) return;
    setAction(kind);
    setIssue("");
    setRun(undefined);
    const value = await operation.run(work);
    if (value) {
      setRun(value);
      setLookup(value.run_id);
      if (value.status !== "running") {
        await client.invalidateQueries({
          queryKey: [mode, "provider-articles"],
        });
        await client.invalidateQueries({
          queryKey: [mode, "video-references"],
        });
      }
    }
  }
  return (
    <section
      id="provider-operations"
      className={styles.section}
      aria-labelledby="provider-heading"
    >
      <div className={styles.sectionHeading}>
        <h2 id="provider-heading">Manual Provider Acquisition</h2>
        <p>Explicit, Bounded Requests</p>
      </div>
      <p className={styles.hint}>
        Requires <code>sources:write</code> and <code>ingestions:write</code>.
        Configuration indicates credentials or a keyless capability; it does not
        prove provider health. No acquisition runs automatically.
      </p>
      {mode !== "real" ? (
        <p className="notice">
          Live provider controls require Real API mode. Provider Status Unknown.
        </p>
      ) : !permitted ? (
        <p className="notice">
          Provider acquisition requires sources:write and ingestions:write
          scopes. Provider Status Unknown.
        </p>
      ) : (
        <>
          <QueryState
            pending={providers.isPending}
            error={providers.error}
            retry={providers.refetch}
          >
            {!providers.data?.length ? (
              <Empty message="No provider capabilities are supplied. No acquisition can be submitted." />
            ) : (
              <div className={styles.providerGrid}>
                {providers.data.map((provider) => (
                  <article
                    className={styles.providerRecord}
                    key={provider.provider}
                  >
                    <h3>{provider.provider}</h3>
                    <strong>{providerConfiguration(provider)}</strong>
                    <p>{provider.mode}</p>
                    <p>
                      {provider.provider === "gdelt"
                        ? "No credential is required for this capability."
                        : "Credential presence is reported; credential validity is not checked here."}
                    </p>
                  </article>
                ))}
              </div>
            )}
            <form
              className={`${styles.form} ${styles.providerForm}`}
              aria-label="Provider Acquisition"
              onSubmit={(event) => {
                event.preventDefault();
                if (!permitted || operation.busy || run?.status === "running")
                  return;
                const form = new FormData(event.currentTarget);
                const query = String(form.get("query")).trim();
                if (query.length < 2) {
                  setIssue(
                    "News Query must contain at least two non-space characters.",
                  );
                  return;
                }
                void perform(
                  (signal) =>
                    adapter.fetchProvider!(
                      String(form.get("provider")) as
                        Api["ProviderStatus"]["provider"] | "all",
                      {
                        query,
                        limit: Number(form.get("limit")),
                        country: (String(form.get("country")) || null) as
                          "in" | "us" | null,
                        retry_failed: false,
                      },
                      signal,
                    ),
                  "acquire",
                );
              }}
            >
              <label>
                Provider
                <select name="provider" disabled={operation.busy}>
                  <option value="all">All Configured Providers</option>
                  {providers.data?.map((provider) => (
                    <option
                      key={provider.provider}
                      value={provider.provider}
                      disabled={!provider.enabled}
                    >
                      {provider.provider}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                News Query
                <input
                  name="query"
                  required
                  defaultValue="technology"
                  minLength={2}
                  maxLength={100}
                  disabled={operation.busy}
                  aria-invalid={!!issue}
                  onInput={() => setIssue("")}
                />
              </label>
              <label>
                Items per Provider
                <input
                  name="limit"
                  type="number"
                  defaultValue={3}
                  min={1}
                  max={30}
                  required
                  disabled={operation.busy}
                />
              </label>
              <label>
                Geography
                <select name="country" disabled={operation.busy}>
                  <option value="">Global</option>
                  <option value="in">India</option>
                  <option value="us">United States</option>
                </select>
              </label>
              <div className={styles.actions}>
                <Button
                  disabled={
                    operation.busy ||
                    run?.status === "running" ||
                    !adapter.fetchProvider ||
                    !providers.data?.some((provider) => provider.enabled)
                  }
                >
                  {operation.busy && action === "acquire"
                    ? "Submitting Acquisition…"
                    : "Fetch Bounded Batch"}
                </Button>
                {issue && (
                  <p className={styles.fieldError} role="alert">
                    {issue}
                  </p>
                )}
              </div>
            </form>
            <p className={styles.hint}>
              Manual requests use provider quotas. Quota remaining is not
              supplied. YouTube acquisition is capped at 10 references.
              Submitted article workflows complete independently; no
              paid-provider retry or background refresh runs here.
            </p>
          </QueryState>
          <form
            aria-label="Provider Run Lookup"
            className={`${styles.form} ${styles.lookup}`}
            onSubmit={(event) => {
              event.preventDefault();
              if (!lookup.trim() || !adapter.providerRun) return;
              void perform(
                (signal) => adapter.providerRun!(lookup.trim(), signal),
                "lookup",
              );
            }}
          >
            <label>
              Provider Run ID
              <input
                required
                value={lookup}
                disabled={operation.busy}
                onChange={(event) => {
                  setLookup(event.target.value);
                  setRun(undefined);
                }}
              />
            </label>
            <Button disabled={operation.busy || !adapter.providerRun}>
              {operation.busy && action === "lookup"
                ? "Checking Provider Run…"
                : "Check Provider Run"}
            </Button>
          </form>
          <OperationError
            error={operation.error}
            write={action === "acquire" ? "provider" : undefined}
          />
          {run && <ProviderRunDetails run={run} />}
        </>
      )}
    </section>
  );
}
function ProviderRunDetails({ run }: { run: Api["ProviderRun"] }) {
  const state =
    run.status === "running"
      ? "Acquisition Running"
      : run.status === "submitted"
        ? "Request Submitted"
        : run.status === "interrupted"
          ? "Acquisition Interrupted"
          : "Provider Status Unknown";
  const finished = !!run.completed_at,
    failed = run.outcomes.some((outcome) => outcome.status === "failed");
  return (
    <section aria-label="Reported Provider Run" className={styles.result}>
      <div className={styles.resultHeading}>
        <h3>{state}</h3>
        <span>Server-Reported Run</span>
      </div>
      <dl className={styles.metadata}>
        <dt>Run ID</dt>
        <dd className={styles.technical}>{run.run_id}</dd>
        <dt>Created At</dt>
        <dd>
          <Timestamp value={run.created_at} />
        </dd>
        <dt>Acquisition Finished At</dt>
        <dd>
          <Timestamp value={run.completed_at} />
        </dd>
        <dt>Acquisition Outcome</dt>
        <dd>
          {finished
            ? failed
              ? "Acquisition Finished With Failures"
              : run.outcomes.some((o) => o.status === "submitted")
                ? "Acquisition Completed"
                : "No Completed Acquisition Reported"
            : "Completion Not Reported"}
        </dd>
      </dl>
      <p className={styles.hint}>
        Acquisition completion describes the provider run. It does not establish
        that submitted articles completed ingestion.
      </p>
      {!run.outcomes.length ? (
        <p>No provider outcomes are reported yet.</p>
      ) : (
        <table role="table" className={styles.table}>
          <caption className="sr-only">Provider Outcomes</caption>
          <thead>
            <tr role="row">
              <th scope="col">Provider</th>
              <th scope="col">Reported Outcome</th>
              <th scope="col">Articles</th>
              <th scope="col">References</th>
            </tr>
          </thead>
          <tbody>
            {run.outcomes.map((outcome) => (
              <tr role="row" key={outcome.provider}>
                <td role="cell">
                  <h3>{outcome.provider}</h3>
                  <EvidenceDisclosure title="Acquisition Details">
                    <dl className={styles.metadata}>
                      {["requests", "skipped", "images", "videos"].map(
                        (field) => (
                          <div className={styles.metadataGroup} key={field}>
                            <dt>
                              {
                                (
                                  {
                                    requests: "Provider Requests",
                                    skipped: "Skipped",
                                    images: "Image References",
                                    videos: "Video References",
                                  } as Record<string, string>
                                )[field]
                              }
                            </dt>
                            <dd>
                              {
                                outcome[
                                  field as
                                    "requests" | "skipped" | "images" | "videos"
                                ]
                              }
                            </dd>
                          </div>
                        ),
                      )}
                    </dl>
                    <pre className={styles.raw}>
                      {JSON.stringify(outcome, null, 2)}
                    </pre>
                  </EvidenceDisclosure>
                </td>
                <td role="cell" data-label="Reported Outcome">
                  {outcome.status === "submitted"
                    ? "Request Submitted"
                    : outcome.status === "failed"
                      ? "Acquisition Failed"
                      : outcome.status === "disabled"
                        ? "Capability Unavailable"
                        : outcome.status}
                  {outcome.error && (
                    <p className={styles.error}>{outcome.error}</p>
                  )}
                </td>
                <td role="cell" data-label="Articles">
                  <dl className={styles.metadata}>
                    <dt>Fetched</dt>
                    <dd>{outcome.fetched}</dd>
                    <dt>Submitted</dt>
                    <dd>{outcome.submitted}</dd>
                    <dt>Duplicates</dt>
                    <dd>{outcome.duplicates}</dd>
                  </dl>
                </td>
                <td role="cell" data-label="Workflow References">
                  {outcome.workflow_ids.length
                    ? outcome.workflow_ids.map((id) => (
                        <p className={styles.technical} key={id}>
                          {id}
                          <br />
                          <span>
                            {workflowState(run.workflow_statuses[id])}
                          </span>
                        </p>
                      ))
                    : "No Workflow References"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <EvidenceDisclosure title="Provider Run Technical Details">
        <pre className={styles.raw}>{JSON.stringify(run, null, 2)}</pre>
      </EvidenceDisclosure>
    </section>
  );
}

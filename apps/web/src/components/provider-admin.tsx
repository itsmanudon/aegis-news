"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "@/lib/generated/api";
import { useConsole } from "./providers";
import { Badge, Panel, QueryState } from "./ui/console";

type Api = components["schemas"];
export function ProviderAdmin() {
  const { adapter, mode, session } = useConsole(),
    client = useQueryClient();
  const permitted =
    !!session?.scopes?.includes("sources:write") &&
    !!session?.scopes?.includes("ingestions:write");
  const [run, setRun] = useState<Api["ProviderRun"]>();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const providers = useQuery({
    queryKey: [mode, "providers"],
    queryFn: ({ signal }) => adapter.providers!(signal),
    enabled: mode === "real" && permitted && !!adapter.providers,
  });
  async function perform(work: () => Promise<Api["ProviderRun"]>) {
    setBusy(true);
    setError("");
    try {
      const value = await work();
      setRun(value);
      if (value.status !== "running") {
        await client.invalidateQueries({
          queryKey: [mode, "provider-articles"],
        });
        await client.invalidateQueries({
          queryKey: [mode, "video-references"],
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider operation failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel title="Manual Provider Acquisition">
      {mode !== "real" ? (
        <p>Live provider controls require Real API mode.</p>
      ) : !permitted ? (
        <p>
          Provider acquisition requires sources:write and ingestions:write
          scopes.
        </p>
      ) : (
        <>
          <QueryState
            pending={providers.isPending}
            error={providers.error}
            retry={providers.refetch}
          >
            <p>
              {providers.data?.map((p) => (
                <span key={p.provider} className="provider-status">
                  <Badge>{p.provider}</Badge>{" "}
                  {p.enabled ? "Enabled" : "Disabled: key missing"}{" "}
                </span>
              ))}
            </p>
            <form
              className="filter-bar"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                void perform(() =>
                  adapter.fetchProvider!(
                    String(form.get("provider")) as
                      Api["ProviderStatus"]["provider"] | "all",
                    {
                      query: String(form.get("query")),
                      limit: Number(form.get("limit")),
                      country: (String(form.get("country")) || null) as
                        "in" | "us" | null,
                      retry_failed: false,
                    },
                  ),
                );
              }}
            >
              <label>
                Provider
                <select name="provider">
                  <option value="all">All Providers</option>
                  {providers.data?.map((p) => (
                    <option
                      key={p.provider}
                      value={p.provider}
                      disabled={!p.enabled}
                    >
                      {p.provider}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                News Query
                <input
                  name="query"
                  defaultValue="technology"
                  minLength={2}
                  maxLength={100}
                  required
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
                />
              </label>
              <label>
                Geography
                <select name="country">
                  <option value="">Global</option>
                  <option value="in">India</option>
                  <option value="us">United States</option>
                </select>
              </label>
              <button disabled={busy || run?.status === "running"}>
                Fetch Bounded Batch
              </button>
            </form>
            <p className="muted">
              Manual acquisition uses provider quotas. YouTube is capped at 10
              references; article ingestion runs through Temporal with the
              configured worker profile.
            </p>
          </QueryState>
          {run && (
            <>
              <p>
                Run <code>{run.run_id}</code> · {run.status}
              </p>
              <button
                disabled={busy}
                onClick={() =>
                  void perform(() => adapter.providerRun!(run.run_id))
                }
              >
                Check Provider Run
              </button>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Status</th>
                      <th>Fetched</th>
                      <th>Submitted</th>
                      <th>Duplicates</th>
                      <th>Videos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run.outcomes?.map((o) => (
                      <tr key={o.provider}>
                        <td>{o.provider}</td>
                        <td>{o.error ?? o.status}</td>
                        <td>{o.fetched}</td>
                        <td>{o.submitted}</td>
                        <td>{o.duplicates}</td>
                        <td>{o.videos}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p>
                Workflow results:{" "}
                {Object.values(run.workflow_statuses ?? {}).join(", ") ||
                  "Not yet reported"}
              </p>
            </>
          )}
          {error && <p role="alert">{error}</p>}
        </>
      )}
    </Panel>
  );
}

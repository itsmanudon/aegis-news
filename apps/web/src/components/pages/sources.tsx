"use client";
import { useState } from "react";
import { ProviderAdmin } from "../provider-admin";
import { useConsole } from "../providers";
import { useSources } from "@/lib/queries";
import { Timestamp } from "../documents/time-rail";
import { Badge, PageHeading, Panel, QueryState } from "../ui/console";
export function Sources() {
  const records = useSources();
  const { adapter, session, mode } = useConsole();
  const [status, setStatus] = useState("");
  const [workflowId, setWorkflowId] = useState("");
  const [pending, setPending] = useState(false);
  async function action(work: () => Promise<void>) {
    setPending(true);
    try {
      await work();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Request failed");
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <PageHeading
        title="Sources / administration"
        description="Manage news sources and submit articles for processing."
      />
      <p className="notice">
        Source and ingestion writes require an authorized identity. Processing
        status is reported by the server.
      </p>
      <ProviderAdmin />
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        <div className="entity-grid">
          {records.data?.map((s) => (
            <Panel
              key={s.source_id}
              title={s.name}
              action={<Badge>{s.kind}</Badge>}
            >
              <dl className="metadata">
                <dt>Source ID</dt>
                <dd className="hash">{s.source_id}</dd>
                <dt>Address</dt>
                <dd>
                  {s.url ? (
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.url}
                    </a>
                  ) : (
                    "Manual upload"
                  )}
                </dd>
                <dt>Created</dt>
                <dd>
                  <Timestamp value={s.created_at} />
                </dd>
                <dt>Configuration</dt>
                <dd>Read-only</dd>
              </dl>
            </Panel>
          ))}
        </div>
      </QueryState>
      <Panel title="Administration">
        {mode === "real" && adapter.createSource && adapter.ingest ? (
          <>
            <form
              className="filter-bar"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                void action(async () => {
                  const source = await adapter.createSource!({
                    name: String(form.get("name")),
                    kind: "upload",
                  });
                  setStatus(`Created source ${source.name}`);
                  await records.refetch();
                });
              }}
            >
              <label>
                Source name
                <input name="name" required maxLength={512} />
              </label>
              <button
                disabled={
                  pending || !session?.scopes?.includes("sources:write")
                }
              >
                Create source
              </button>
            </form>
            <form
              className="filter-bar"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                void action(async () => {
                  const bytes = new TextEncoder().encode(
                    String(form.get("text")),
                  );
                  const content = btoa(
                    Array.from(bytes, (b) => String.fromCharCode(b)).join(""),
                  );
                  const result = await adapter.ingest!({
                    source_id: String(form.get("source")),
                    title: String(form.get("title")),
                    content_type: "text/plain",
                    media: [],
                    content_base64: content,
                    language: "en",
                    idempotency_key: String(form.get("key")),
                    correlation_id: crypto.randomUUID(),
                  });
                  setWorkflowId(result.workflow_id);
                  setStatus(
                    "Article accepted for processing. Check its run status below.",
                  );
                });
              }}
            >
              <label>
                Source
                <select name="source" required>
                  {records.data?.map((s) => (
                    <option key={s.source_id} value={s.source_id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Article title
                <input name="title" required maxLength={512} />
              </label>
              <label>
                Article text
                <textarea name="text" required maxLength={100000} />
              </label>
              <label>
                Submission key
                <input
                  name="key"
                  required
                  placeholder="Unique key; reuse when retrying"
                  maxLength={512}
                />
              </label>
              <button
                disabled={
                  pending || !session?.scopes?.includes("ingestions:write")
                }
              >
                Submit article
              </button>
            </form>
            {workflowId && (
              <p>
                <code>{workflowId}</code>{" "}
                <button
                  disabled={pending}
                  onClick={() =>
                    void action(async () => {
                      const run = await adapter.ingestionRun!(workflowId);
                      setStatus(JSON.stringify(run));
                    })
                  }
                >
                  Check processing status
                </button>
              </p>
            )}
            <p role="status">{status}</p>
            {!session?.scopes?.includes("ingestions:write") && (
              <p>Source creation and ingestion require additional scopes.</p>
            )}
          </>
        ) : (
          <p>
            Source creation and article submission are available in Real API
            mode.
          </p>
        )}
      </Panel>
    </>
  );
}

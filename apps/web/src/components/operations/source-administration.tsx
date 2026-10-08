"use client";
import { useId, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Domain } from "@/lib/models";
import type { components } from "@/lib/generated/api";
import {
  FormIssue,
  ingestionItems,
  record,
  type ArticleDraft,
} from "@/lib/operations";
import { useConsole } from "../providers";
import { Button } from "../ui/console";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { useOperation } from "./use-operation";
import { OperationError } from "./operation-feedback";
import { WorkflowStatus } from "./workflow-status";
import styles from "./operations.module.css";
type Source = Domain["Source"];
export function SourceAdministration({ sources }: { sources: Source[] }) {
  const [created, setCreated] = useState<Source>();
  const [workflow, setWorkflow] = useState("");
  const choices =
    created && !sources.some((s) => s.source_id === created.source_id)
      ? [created, ...sources]
      : sources;
  return (
    <>
      <div className={styles.forms}>
        <SourceCreation onCreated={setCreated} />
        <ArticleSubmission sources={choices} onAccepted={setWorkflow} />
      </div>
      <WorkflowLookup key={workflow} suggested={workflow} />
    </>
  );
}
function SourceCreation({
  onCreated,
}: {
  onCreated: (source: Source) => void;
}) {
  const { adapter, mode, session } = useConsole(),
    client = useQueryClient(),
    operation = useOperation(),
    id = useId();
  const [created, setCreated] = useState<Source>(),
    [issue, setIssue] = useState("");
  const permitted =
    mode === "real" &&
    !!adapter.createSource &&
    !!session?.scopes?.includes("sources:write");
  return (
    <section className={styles.formPanel}>
      <h2>Create Source</h2>
      <p className={styles.hint}>
        Requires <code>sources:write</code>. Source creation registers metadata;
        it does not acquire articles.
      </p>
      {mode !== "real" && (
        <p className={styles.hint}>
          Source creation is available in Real API mode.
        </p>
      )}
      <form
        className={styles.form}
        aria-label="Source Creation"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!permitted || operation.busy) return;
          const form = new FormData(event.currentTarget),
            name = String(form.get("name")).trim();
          if (!name) {
            setIssue("Source Name must contain text.");
            return;
          }
          setIssue("");
          setCreated(undefined);
          const value = await operation.run((signal) =>
            adapter.createSource!(
              {
                name,
                kind: String(
                  form.get("kind"),
                ) as components["schemas"]["SourceCreate"]["kind"],
                url: String(form.get("url")) || null,
              },
              signal,
            ),
          );
          if (value) {
            setCreated(value);
            onCreated(value);
            await client.invalidateQueries({ queryKey: [mode, "source-page"] });
            await client.invalidateQueries({ queryKey: [mode, "sources"] });
          }
        }}
      >
        <fieldset disabled={!permitted || operation.busy}>
          <label>
            Source Name
            <input
              aria-label="Source Name"
              name="name"
              required
              maxLength={512}
              aria-describedby={`${id}-name${issue ? ` ${id}-name-error` : ""}`}
              aria-invalid={!!issue}
              onInput={() => setIssue("")}
            />
            <small id={`${id}-name`}>
              A readable name for this registered source.
            </small>
            {issue && (
              <span
                id={`${id}-name-error`}
                className={styles.fieldError}
                role="alert"
              >
                {issue}
              </span>
            )}
          </label>
          <label>
            Source Type
            <select name="kind" defaultValue="upload">
              <option value="upload">Upload</option>
              <option value="feed">Feed</option>
              <option value="api">API</option>
              <option value="web">Web</option>
            </select>
          </label>
          <label>
            Source URL
            <input
              aria-label="Source URL"
              name="url"
              type="url"
              pattern="https?://.*"
              aria-describedby={`${id}-url`}
            />
            <small id={`${id}-url`}>
              Optional HTTP or HTTPS source address. No automatic fetching
              occurs.
            </small>
          </label>
        </fieldset>
        <Button disabled={!permitted || operation.busy}>
          {operation.busy ? "Creating Source…" : "Create Source"}
        </Button>
      </form>
      <OperationError error={operation.error} />
      {created && (
        <div role="status" className={styles.result}>
          <strong>Source Created</strong>
          <p>{created.name}</p>
          <p className={styles.technical}>{created.source_id}</p>
        </div>
      )}
      {!permitted && mode === "real" && (
        <p className={styles.hint}>
          An authenticated identity with sources:write is required.
        </p>
      )}
    </section>
  );
}
function ArticleSubmission({
  sources,
  onAccepted,
}: {
  sources: Source[];
  onAccepted: (workflow: string) => void;
}) {
  const { adapter, mode, session } = useConsole(),
    operation = useOperation(),
    id = useId();
  const [drafts, setDrafts] = useState<(ArticleDraft & { id: number })[]>([
    { id: 1, title: "", text: "", key: "" },
  ]);
  const [source, setSource] = useState<Source>(),
    [issue, setIssue] = useState<FormIssue>(),
    [accepted, setAccepted] = useState<Record<string, unknown>>();
  const permitted =
    mode === "real" &&
    !!adapter.ingest &&
    !!session?.scopes?.includes("ingestions:write");
  const choices =
    source && !sources.some((s) => s.source_id === source.source_id)
      ? [source, ...sources]
      : sources;
  function update(index: number, field: keyof ArticleDraft, value: string) {
    setDrafts((current) =>
      current.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      ),
    );
    setIssue(undefined);
  }
  const references = accepted
    ? (Array.isArray(accepted.submissions) ? accepted.submissions : [accepted])
        .map(record)
        .filter((r): r is Record<string, unknown> => !!r)
    : [];
  return (
    <section className={styles.formPanel}>
      <h2>Submit Articles</h2>
      <p className={styles.hint}>
        Requires <code>ingestions:write</code>. Submit captured plain text;
        acceptance does not establish processing completion.
      </p>
      {mode !== "real" && (
        <p className={styles.hint}>
          Article submission is available in Real API mode.
        </p>
      )}
      <form
        aria-label="Article Submission"
        className={styles.form}
        onSubmit={async (event) => {
          event.preventDefault();
          if (!permitted || operation.busy) return;
          let items: components["schemas"]["IngestionRequest"][];
          try {
            items = ingestionItems(source?.source_id ?? "", drafts);
          } catch (error) {
            if (error instanceof FormIssue) setIssue(error);
            return;
          }
          setIssue(undefined);
          setAccepted(undefined);
          const value = await operation.run((signal) =>
            items.length === 1
              ? adapter.ingest!(items[0], signal)
              : adapter.ingestBatch!({ items }, signal),
          );
          if (value) {
            setAccepted(value);
            const first = record(
              Array.isArray(value.submissions) ? value.submissions[0] : value,
            );
            if (typeof first?.workflow_id === "string")
              onAccepted(first.workflow_id);
          }
        }}
      >
        <fieldset disabled={!permitted || operation.busy}>
          <label>
            Source
            <select
              aria-label="Source"
              value={source?.source_id ?? ""}
              required
              aria-invalid={issue?.field === "source"}
              onChange={(event) => {
                setSource(
                  choices.find((s) => s.source_id === event.target.value),
                );
                setIssue(undefined);
              }}
              aria-describedby={`${id}-source${issue?.field === "source" ? ` ${id}-batch-error` : ""}`}
            >
              <option value="">Select a Registered Source</option>
              {choices.map((s) => (
                <option key={s.source_id} value={s.source_id}>
                  {s.name}
                </option>
              ))}
            </select>
            <small id={`${id}-source`}>
              Choose from the loaded registry page or a source created in this
              session. Browse registry pages to select another source.
            </small>
          </label>
          {drafts.map((draft, index) => (
            <fieldset key={draft.id} className={styles.article}>
              <legend>
                {drafts.length === 1
                  ? "Captured Article"
                  : `Article ${index + 1}`}
              </legend>
              <label>
                Article Title
                <input
                  required
                  maxLength={512}
                  value={draft.title}
                  onChange={(event) =>
                    update(index, "title", event.target.value)
                  }
                  aria-invalid={issue?.field === `${index}.title`}
                  aria-describedby={
                    issue?.field === `${index}.title`
                      ? `${id}-issue-${draft.id}`
                      : undefined
                  }
                />
              </label>
              <label>
                Article Text
                <textarea
                  aria-label="Article Text"
                  required
                  maxLength={262144}
                  value={draft.text}
                  onChange={(event) =>
                    update(index, "text", event.target.value)
                  }
                  aria-describedby={`${id}-text-${draft.id}${issue?.field === `${index}.text` ? ` ${id}-issue-${draft.id}` : ""}`}
                  aria-invalid={issue?.field === `${index}.text`}
                />
                <small id={`${id}-text-${draft.id}`}>
                  Captured plain text, at most 256 KiB when encoded as UTF-8. No
                  attachments are submitted by this form.
                </small>
              </label>
              <label>
                Submission Key
                <input
                  aria-label="Submission Key"
                  required
                  maxLength={512}
                  value={draft.key}
                  onChange={(event) => update(index, "key", event.target.value)}
                  aria-describedby={`${id}-key-${draft.id}${issue?.field === `${index}.key` ? ` ${id}-issue-${draft.id}` : ""}`}
                  aria-invalid={issue?.field === `${index}.key`}
                />
                <small id={`${id}-key-${draft.id}`}>
                  Use a distinct key per article. Keep the same key and content
                  when retrying an uncertain request.
                </small>
              </label>
              {issue?.field.startsWith(`${index}.`) && (
                <p
                  id={`${id}-issue-${draft.id}`}
                  className={styles.fieldError}
                  role="alert"
                >
                  {issue.message}
                </p>
              )}
              {drafts.length > 1 && (
                <Button
                  className="secondary"
                  type="button"
                  onClick={() => {
                    setDrafts((items) =>
                      items.filter((i) => i.id !== draft.id),
                    );
                    setIssue(undefined);
                  }}
                >
                  Remove Article {index + 1}
                </Button>
              )}
            </fieldset>
          ))}
        </fieldset>
        {issue && !issue.field.includes(".") && (
          <p
            id={`${id}-batch-error`}
            className={styles.fieldError}
            role="alert"
          >
            {issue.message}
          </p>
        )}
        <div className={styles.actions}>
          <Button
            disabled={
              !permitted ||
              operation.busy ||
              (drafts.length > 1 && !adapter.ingestBatch)
            }
          >
            {operation.busy
              ? "Submitting Articles…"
              : drafts.length > 1
                ? "Submit Batch"
                : "Submit Article"}
          </Button>
          <Button
            type="button"
            className="secondary"
            disabled={
              !permitted ||
              operation.busy ||
              drafts.length >= 20 ||
              !adapter.ingestBatch
            }
            onClick={() =>
              setDrafts((items) => [
                ...items,
                {
                  id: Math.max(...items.map((i) => i.id)) + 1,
                  title: "",
                  text: "",
                  key: "",
                },
              ])
            }
          >
            Add Another Article
          </Button>
        </div>
        <p className={styles.hint}>
          Batches contain at most 20 articles and must fit within the encoded
          request limit. A failed batch may be partially accepted; retry the
          unchanged batch with the same keys. Submission is never retried
          automatically.
        </p>
      </form>
      <OperationError error={operation.error} />
      {accepted && (
        <div className={styles.result} role="status">
          <strong>Request Accepted</strong>
          <p className={styles.hint}>
            Only acceptance is confirmed. Look up a returned workflow to inspect
            its reported state.
          </p>
          {references.map((reference, i) => (
            <div key={i}>
              <p className={styles.technical}>
                {typeof reference.workflow_id === "string"
                  ? reference.workflow_id
                  : "Workflow Reference Not Supplied"}
              </p>
              {typeof reference.workflow_id === "string" && (
                <Button
                  className="secondary"
                  type="button"
                  onClick={() => onAccepted(String(reference.workflow_id))}
                >
                  Inspect Workflow {i + 1}
                </Button>
              )}
            </div>
          ))}
          <EvidenceDisclosure title="Submission References">
            <pre className={styles.raw}>
              {JSON.stringify(accepted, null, 2)}
            </pre>
          </EvidenceDisclosure>
        </div>
      )}
      {!permitted && mode === "real" && (
        <p className={styles.hint}>
          An authenticated identity with ingestions:write is required.
        </p>
      )}
    </section>
  );
}
function WorkflowLookup({ suggested }: { suggested: string }) {
  const { adapter, mode, session } = useConsole(),
    operation = useOperation(),
    [run, setRun] = useState<Record<string, unknown>>(),
    [issue, setIssue] = useState("");
  const permitted =
    mode === "real" &&
    !!adapter.ingestionRun &&
    !!session?.scopes?.includes("documents:read");
  return (
    <section className={styles.lookup} id="workflow-lookup">
      <h2>Known Workflow</h2>
      <p className={styles.hint}>
        Requires <code>documents:read</code>. Look up a known workflow ID. The
        API does not supply a global pipeline history.
      </p>
      <form
        className={styles.form}
        aria-label="Workflow Lookup"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!permitted || operation.busy) return;
          const id = String(
            new FormData(event.currentTarget).get("workflow"),
          ).trim();
          if (!id) {
            setIssue("Enter a known workflow ID.");
            return;
          }
          setIssue("");
          setRun(undefined);
          const value = await operation.run((signal) =>
            adapter.ingestionRun!(id, signal),
          );
          if (value) setRun(value);
        }}
      >
        <label>
          Workflow ID
          <input
            name="workflow"
            required
            defaultValue={suggested}
            disabled={!permitted || operation.busy}
            onInput={() => {
              setIssue("");
              setRun(undefined);
            }}
            aria-invalid={!!issue}
          />
          {issue && (
            <span className={styles.fieldError} role="alert">
              {issue}
            </span>
          )}
        </label>
        <Button disabled={!permitted || operation.busy}>
          {operation.busy ? "Checking Workflow…" : "Check Processing Status"}
        </Button>
      </form>
      <OperationError error={operation.error} />
      {run && <WorkflowStatus run={run} />}
      {!permitted && (
        <p className={styles.hint}>
          Workflow lookup is available in Real API mode to an identity with
          documents:read.
        </p>
      )}
    </section>
  );
}

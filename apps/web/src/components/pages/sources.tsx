"use client";
import { useSources } from "@/lib/queries";
import { Timestamp } from "../documents/time-rail";
import { Badge, PageHeading, Panel, QueryState } from "../ui/console";
export function Sources() {
  const records = useSources();
  return (
    <>
      <PageHeading
        title="Sources / administration"
        description="Source registry and the future administration boundary."
      />
      <p className="notice">
        Read-only source shell. Configuration and permission controls await the
        source and authentication contracts.
      </p>
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
        <p className="panel-intro">
          Source editing, user management and policy controls will become
          available after server authorization is integrated.
        </p>
      </Panel>
    </>
  );
}

"use client";
import Link from "next/link";
import { useDocuments, useEntities, useEntity } from "@/lib/queries";
import { DocumentTable } from "../documents/document-table";
import { Timestamp } from "../documents/time-rail";
import { Badge, PageHeading, Panel, QueryState } from "../ui/console";
export function Entities() {
  const records = useEntities();
  return (
    <>
      <PageHeading
        title="Entity Register"
        description="Inspect canonical entities and the source evidence associated with them."
      />
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        <div className="entity-grid">
          {records.data?.map((e) => (
            <Panel
              key={e.entity_id}
              title={e.canonical_name}
              action={<Badge>{e.kind}</Badge>}
            >
              <p className="hash">{e.entity_id}</p>
              <p>
                Created <Timestamp value={e.created_at} />
              </p>
              <Link href={`/entities/${e.entity_id}`}>Inspect Entity →</Link>
            </Panel>
          ))}
        </div>
      </QueryState>
    </>
  );
}
export function EntityDetail({ id }: { id: string }) {
  const entity = useEntity(id),
    records = useDocuments({ entityId: id });
  const related = records.data ?? [];
  return (
    <>
      <Link className="back-link" href="/entities">
        ← Entity Register
      </Link>
      <PageHeading
        title={entity.data?.canonical_name ?? "Entity Detail"}
        description="Canonical identity and linked evidence. Associations require analyst review."
      />
      <QueryState
        pending={entity.isPending}
        error={entity.error}
        retry={entity.refetch}
      >
        {entity.data && (
          <Panel
            title="Canonical Record"
            action={<Badge>{entity.data.kind}</Badge>}
          >
            <dl className="metadata">
              <dt>Entity ID</dt>
              <dd className="hash">{entity.data.entity_id}</dd>
              <dt>Created</dt>
              <dd>
                <Timestamp value={entity.data.created_at} />
              </dd>
              <dt>Schema</dt>
              <dd>{entity.data.schema_version}</dd>
            </dl>
          </Panel>
        )}
      </QueryState>
      <Panel title="Associated Documents">
        <QueryState
          pending={records.isPending}
          error={records.error}
          retry={records.refetch}
        >
          <DocumentTable documents={related} />
        </QueryState>
      </Panel>
    </>
  );
}

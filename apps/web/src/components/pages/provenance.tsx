"use client";
import Link from "next/link";
import { useDocuments } from "@/lib/queries";
import { ProvenanceCard } from "../documents/provenance-card";
import { PageHeading, QueryState } from "../ui/console";
export function Provenance() {
  const records = useDocuments();
  return (
    <>
      <PageHeading
        title="Provenance / Integrity"
        description="Inspect content lineage, signature state and verification outcomes."
      />
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        <div className="provenance-grid">
          {records.data?.map((v) => (
            <div key={v.document.document_id}>
              <Link
                className="provenance-document"
                href={`/documents/${v.document.document_id}`}
              >
                {v.document.title}
              </Link>
              <ProvenanceCard view={v} />
            </div>
          ))}
        </div>
      </QueryState>
    </>
  );
}

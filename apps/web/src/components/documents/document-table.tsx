import Link from "next/link";
import type { DocumentView } from "@/lib/models";
import { Badge, Empty } from "../ui/console";
import { Timestamp } from "./time-rail";
export function DocumentTable({ documents }: { documents: DocumentView[] }) {
  if (!documents.length) return <Empty />;
  return (
    <div className="table-scroll">
      <table>
        <caption className="sr-only">
          Documents and intelligence availability
        </caption>
        <thead>
          <tr>
            <th scope="col">Document / Source</th>
            <th scope="col">Published</th>
            <th scope="col">First Seen</th>
            <th scope="col">Intelligence</th>
            <th scope="col">Integrity</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((v) => (
            <tr key={v.document.document_id}>
              <td>
                <Link
                  className="document-title"
                  href={`/documents/${v.document.document_id}`}
                >
                  {v.document.title}
                </Link>
                <span className="row-meta">
                  {v.source.name} · {v.source.kind} ·{" "}
                  {v.document.language ?? "Unknown Language"}
                </span>
              </td>
              <td className="date-cell">
                <Timestamp value={v.document.published_at} />
              </td>
              <td className="date-cell">
                <Timestamp value={v.document.first_seen_at} />
              </td>
              <td>
                {v.intelligenceLoaded === false ? (
                  <span>Open detail for analysis</span>
                ) : v.analyses.length ? (
                  <>
                    <Badge tone="model">Model Assessment</Badge>
                    <span className="row-meta">
                      {v.analyses.length} analyses ·{" "}
                      <Timestamp
                        value={v.analyses.map((a) => a.available_at).sort()[0]}
                      />
                    </span>
                  </>
                ) : (
                  <Badge>Pending</Badge>
                )}
              </td>
              <td>
                <Badge tone={v.integrity}>{v.integrity}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

"use client";
import Link from "next/link";
import { Fragment, useId, useRef, useState } from "react";
import type { DocumentView } from "@/lib/models";
import { Badge, Empty } from "../ui/console";
import { Timestamp } from "./time-rail";
import { EvidenceDetails } from "./evidence-details";
import { useConsole } from "../providers";
export function DocumentTable({
  documents,
  expandable = false,
}: {
  documents: DocumentView[];
  expandable?: boolean;
}) {
  const [expanded, setExpanded] = useState<string[]>([]);
  const { mode } = useConsole();
  const prefix = useId();
  const buttons = useRef(new Map<string, HTMLButtonElement>());
  const toggle = (id: string) =>
    setExpanded((values) =>
      values.includes(id)
        ? values.filter((value) => value !== id)
        : [...values, id],
    );
  if (!documents.length) return <Empty />;
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Evidence Table; Horizontally Scrollable"
    >
      <table>
        <caption className="sr-only">
          Documents and intelligence availability
        </caption>
        <thead>
          <tr>
            {expandable && <th scope="col">Details</th>}
            <th scope="col">Document / Source</th>
            <th scope="col">Published</th>
            <th scope="col">First Seen</th>
            <th scope="col">Intelligence</th>
            <th scope="col">Integrity</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((v) => (
            <Fragment key={v.document.document_id}>
              <tr>
                {expandable && (
                  <td>
                    <button
                      ref={(element) => {
                        if (element)
                          buttons.current.set(v.document.document_id, element);
                        else buttons.current.delete(v.document.document_id);
                      }}
                      type="button"
                      aria-label={
                        expanded.includes(v.document.document_id)
                          ? "Collapse Evidence"
                          : "Expand Evidence"
                      }
                      aria-expanded={expanded.includes(v.document.document_id)}
                      aria-controls={`${prefix}-${v.document.document_id}`}
                      onClick={() => toggle(v.document.document_id)}
                      onKeyDown={(event) => {
                        if (
                          event.key === "Escape" &&
                          expanded.includes(v.document.document_id)
                        ) {
                          event.stopPropagation();
                          toggle(v.document.document_id);
                        }
                      }}
                    >
                      <span aria-hidden="true">
                        {expanded.includes(v.document.document_id) ? "⌃" : "⌄"}
                      </span>
                    </button>
                  </td>
                )}
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
                          value={
                            v.analyses.map((a) => a.available_at).sort()[0]
                          }
                        />
                      </span>
                    </>
                  ) : (
                    <Badge>No Assessments Available</Badge>
                  )}
                </td>
                <td>
                  <Badge tone={v.integrity}>{v.integrity}</Badge>
                </td>
              </tr>
              {expandable && expanded.includes(v.document.document_id) && (
                <tr className="expanded-table-row">
                  <td colSpan={6}>
                    <div
                      id={`${prefix}-${v.document.document_id}`}
                      role="region"
                      aria-label={`Evidence for ${v.document.title}`}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          event.stopPropagation();
                          toggle(v.document.document_id);
                          buttons.current.get(v.document.document_id)?.focus();
                        }
                      }}
                    >
                      <EvidenceDetails view={v} simulated={mode === "mock"} />
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

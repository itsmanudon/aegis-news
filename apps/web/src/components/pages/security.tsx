"use client";
import { useState } from "react";
import { useAudit } from "@/lib/queries";
import { useConsole } from "../providers";
import { Timestamp } from "../documents/time-rail";
import { Badge, Empty, PageHeading, Panel, QueryState } from "../ui/console";
export function Security() {
  const records = useAudit(),
    { session } = useConsole();
  const [outcome, setOutcome] = useState("");
  const entries =
    records.data?.filter((e) => !outcome || e.outcome === outcome) ?? [];
  return (
    <>
      <PageHeading
        title="Audit / security"
        description="Review access decisions and integrity signals with explicit identity context."
      />
      <div className="two-column">
        <Panel title="Session context">
          <dl className="metadata">
            <dt>Identity</dt>
            <dd>{session?.displayName ?? "Anonymous"}</dd>
            <dt>State</dt>
            <dd>{session?.state ?? "Loading"}</dd>
            <dt>Roles</dt>
            <dd>{session?.roles.join(", ") || "None"}</dd>
            <dt>Provider</dt>
            <dd>
              {session?.simulated
                ? "Mock identity adapter"
                : "OIDC integration pending"}
            </dd>
          </dl>
        </Panel>
        <Panel title="Security integration">
          <p className="panel-intro">
            Session display is not an authorization decision. Server
            permissions, signed verification and durable audit history will be
            supplied by the security service.
          </p>
          <Badge tone="unverified">Integration pending</Badge>
        </Panel>
      </div>
      <div className="standalone-filter">
        <label htmlFor="audit-outcome">Outcome</label>
        <select
          id="audit-outcome"
          value={outcome}
          onChange={(e) => setOutcome(e.target.value)}
        >
          <option value="">All outcomes</option>
          <option value="allowed">Allowed</option>
          <option value="denied">Denied</option>
          <option value="warning">Warning</option>
        </select>
      </div>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {!entries.length ? (
          <Empty />
        ) : (
          <div className="table-scroll">
            <table>
              <caption className="sr-only">Audit entries</caption>
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Action</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Outcome</th>
                  <th scope="col">Subject</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <Timestamp value={e.at} />
                    </td>
                    <td>{e.action}</td>
                    <td>{e.actor}</td>
                    <td>
                      <Badge
                        tone={e.outcome === "allowed" ? "verified" : "failed"}
                      >
                        {e.outcome}
                      </Badge>
                    </td>
                    <td className="hash">{e.subject}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryState>
    </>
  );
}

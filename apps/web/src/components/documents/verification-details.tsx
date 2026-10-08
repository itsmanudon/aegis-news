import type { Verification } from "@/lib/models";
import { Timestamp } from "./time-rail";
export function VerificationDetails({ value }: { value: Verification }) {
  const label = (result?: boolean) =>
    result === undefined ? "Not Reported" : result ? "Passed" : "Not Valid";
  return (
    <>
      <dl className="verification-checks">
        <div>
          <dt>Content Integrity</dt>
          <dd>{label(value.contentVerified)}</dd>
        </div>
        <div>
          <dt>Chain Validity</dt>
          <dd>{label(value.chainValid)}</dd>
        </div>
        <div>
          <dt>Digital Signature</dt>
          <dd>
            {value.signatureValid === undefined
              ? value.signature
              : label(value.signatureValid)}
          </dd>
        </div>
      </dl>
      <p className="muted">
        These checks address captured bytes and lineage, not the factual truth
        of the report.
      </p>
      <div className="receipt-time">
        Response Received At <Timestamp value={value.responseReceivedAt} />
      </div>
      <p className="muted">
        Browser receipt time; no server-attested verification timestamp was
        supplied.
      </p>
    </>
  );
}

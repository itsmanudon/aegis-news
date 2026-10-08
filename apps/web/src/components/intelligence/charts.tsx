import type { components } from "@/lib/generated/api";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import styles from "./intelligence.module.css";
export function CoverageChart({
  buckets,
}: {
  buckets: components["schemas"]["CoverageBucket"][];
}) {
  if (!buckets.length)
    return (
      <p role="status">
        No observations are recorded within this population and interval.
      </p>
    );
  const sorted = [...buckets].sort((a, b) => a.day.localeCompare(b.day));
  const first = Date.parse(sorted[0].day),
    last = Date.parse(sorted.at(-1)!.day),
    maximum = Math.max(...sorted.map((value) => value.document_count), 1);
  const points = sorted.map((bucket) => ({
    x:
      40 +
      (last === first
        ? 260
        : ((Date.parse(bucket.day) - first) / (last - first)) * 520),
    y: 170 - (bucket.document_count / maximum) * 140,
    ...bucket,
  }));
  return (
    <div className={styles.chart}>
      <svg
        viewBox="0 0 600 220"
        role="img"
        aria-label="Recorded Documents by Observed UTC Day"
      >
        <title>Recorded Document Coverage</title>
        <desc>
          Only recorded UTC-day observations. Exact values are available in
          Coverage Data.
        </desc>
        <line x1="40" y1="170" x2="560" y2="170" className={styles.axis} />
        <text x="10" y="34">
          {maximum}
        </text>
        <text x="15" y="174">
          0
        </text>
        {points.length > 1 && (
          <polyline
            points={points.map((point) => `${point.x},${point.y}`).join(" ")}
            className={styles.line}
          />
        )}
        {points.map((point) => (
          <circle
            key={point.day}
            cx={point.x}
            cy={point.y}
            r="4"
            className={styles.point}
          >
            <title>
              {point.day}: {point.document_count} recorded documents
            </title>
          </circle>
        ))}
        <text x="40" y="204">
          {sorted[0].day}
        </text>
        <text x="560" y="204" textAnchor="end">
          {sorted.at(-1)!.day}
        </text>
      </svg>
      <p className={styles.caption}>
        Recorded Documents. Only observed days are plotted; the line connects
        observations. Missing days are not inferred values or forecasts.
      </p>
      <EvidenceDisclosure title="Coverage Data">
        <table className={styles.dataTable}>
          <caption className="sr-only">Observed UTC-Day Coverage</caption>
          <thead>
            <tr>
              <th scope="col">UTC Day</th>
              <th scope="col">Documents</th>
              <th scope="col">Classified Documents</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((bucket) => (
              <tr key={bucket.day}>
                <th scope="row">{bucket.day}</th>
                <td>{bucket.document_count}</td>
                <td>{bucket.classified_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </EvidenceDisclosure>
    </div>
  );
}
export function Distribution({
  label,
  denominator,
  values,
}: {
  label: string;
  denominator: number;
  values: { name: string; count: number }[];
}) {
  return (
    <div aria-label={label} className={styles.distribution}>
      {!values.length ? (
        <p>No classifications or distribution records are supplied.</p>
      ) : (
        values.map((value, index) => (
          <div className={styles.barRow} key={`${value.name}:${index}`}>
            <div>
              <span>{value.name}</span>
              <strong>
                {value.count} of {denominator}
              </strong>
            </div>
            <meter
              min={0}
              max={Math.max(1, denominator)}
              value={value.count}
              aria-label={`${value.name}: ${value.count} of ${denominator}`}
            >
              {value.count}
            </meter>
          </div>
        ))
      )}
    </div>
  );
}

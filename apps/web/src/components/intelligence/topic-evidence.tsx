import type { components } from "@/lib/generated/api";
import Link from "next/link";
import { literalExcerpt } from "@/lib/source-presentation";
import { Timestamp } from "../documents/time-rail";
import { Badge } from "../ui/console";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import styles from "./intelligence.module.css";
export function TopicEvidence({
  member,
  simulated,
}: {
  member: components["schemas"]["TopicMembership"];
  simulated: boolean;
}) {
  return (
    <article className={`topic-evidence ${styles.evidence}`}>
      <div>
        <strong>{member.source.name}</strong>
        <dl className="evidence-times">
          <div>
            <dt>Published</dt>
            <dd>
              <Timestamp value={member.document.published_at} />
            </dd>
          </div>
          <div>
            <dt>First Seen</dt>
            <dd>
              <Timestamp value={member.document.first_seen_at} />
            </dd>
          </div>
        </dl>
      </div>
      <div>
        <h3>
          <Link
            href={`/documents/${encodeURIComponent(member.document.document_id)}`}
          >
            {member.document.title}
          </Link>
        </h3>
        {member.document.text &&
        member.document.text.trim() !== member.document.title.trim() ? (
          <p className={styles.excerpt}>
            <strong>Source Excerpt</strong>{" "}
            {literalExcerpt(member.document.text, 260)}
          </p>
        ) : (
          <p className={styles.caption}>
            Only headline text is available in this record.
          </p>
        )}
        <Link
          href={`/documents/${encodeURIComponent(member.document.document_id)}`}
        >
          Full Story →
        </Link>
        <EvidenceDisclosure title="Topic Assessment">
          <Badge tone="model">
            {simulated ? "Simulated Model Assessment" : "Model Assessment"}
          </Badge>
          <dl className="metadata">
            <dt>Model</dt>
            <dd>
              {member.model.model_name} · {member.model.model_version}
            </dd>
            <dt>Provider</dt>
            <dd>{member.model.provider}</dd>
            <dt>Reported Confidence</dt>
            <dd>
              {new Intl.NumberFormat("en", {
                style: "percent",
                maximumFractionDigits: 1,
              }).format(member.confidence)}
            </dd>
            <dt>Intelligence Available</dt>
            <dd>
              <Timestamp value={member.available_at} />
            </dd>
            <dt>Analysis ID</dt>
            <dd className={styles.technical}>{member.analysis_id}</dd>
            <dt>Configuration Hash</dt>
            <dd className={styles.technical}>
              {member.model.configuration_hash}
            </dd>
          </dl>
          <p className={styles.caption}>
            Topic membership and confidence are model outputs. They do not
            establish the accuracy of the reporting or a verified provenance
            result.
          </p>
        </EvidenceDisclosure>
      </div>
    </article>
  );
}
export function TopicIdentity({
  topic,
}: {
  topic: components["schemas"]["TopicSummary"];
}) {
  return (
    <div className={styles.identity}>
      <div>
        <p className={styles.model}>
          {topic.model.provider} · {topic.model.model_name} ·{" "}
          {topic.model.model_version}
        </p>
        <p>
          {topic.document_count} unique documents in this model cohort at the
          query cutoff.
        </p>
        <dl className="evidence-times">
          <div>
            <dt>First Selected Assessment</dt>
            <dd>
              <Timestamp value={topic.first_available_at} />
            </dd>
          </div>
          <div>
            <dt>Latest Selected Assessment</dt>
            <dd>
              <Timestamp value={topic.latest_available_at} />
            </dd>
          </div>
        </dl>
      </div>
      <EvidenceDisclosure title="Topic Identity">
        <dl className="metadata">
          <dt>Grouping</dt>
          <dd>Exact label, provider, model, version and configuration</dd>
          <dt>Topic ID</dt>
          <dd className={styles.technical}>{topic.topic_id}</dd>
          <dt>Configuration Hash</dt>
          <dd className={styles.technical}>{topic.model.configuration_hash}</dd>
        </dl>
        <p className={styles.caption}>{topic.selection_policy}</p>
      </EvidenceDisclosure>
    </div>
  );
}

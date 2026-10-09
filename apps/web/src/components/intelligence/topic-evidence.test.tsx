import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
  fixtureTopics,
  fixtureTopicDocuments,
} from "@/lib/intelligence-fixtures";
import { TopicEvidence, TopicIdentity } from "./topic-evidence";
const topic = fixtureTopics({ cutoff: "2026-10-03T09:00:00Z" }).data[0];
const member = fixtureTopicDocuments(topic.topic_id, { cutoff: topic.as_of })
  .data[0];
it("topic evidence preserves source preview, separate story link and actual model availability", () => {
  const html = renderToStaticMarkup(
    <TopicEvidence member={member} simulated={false} />,
  );
  expect(html).toContain(member.source.name);
  expect(html).toContain("Source Excerpt");
  expect(html).toContain(member.analysis_id);
  expect(html).toContain("Intelligence Available");
  expect(html).toContain("Full Story");
  expect(html).toContain("<summary");
});
it("topic evidence preserves zero confidence and labels simulated assessments", () => {
  const html = renderToStaticMarkup(
    <TopicEvidence member={{ ...member, confidence: 0 }} simulated />,
  );
  expect(html).toContain("0%");
  expect(html).toContain("Simulated Model Assessment");
  expect(html).not.toContain("Verified");
});
it("topic identity identifies its model cohort and real deduplicated population", () => {
  const html = renderToStaticMarkup(<TopicIdentity topic={topic} />);
  expect(html).toContain(topic.model.model_name);
  expect(html).toContain("0.3.1");
  expect(html).toContain("unique documents");
  expect(html).toContain("Topic Identity");
  expect(html).not.toContain("Trending");
});

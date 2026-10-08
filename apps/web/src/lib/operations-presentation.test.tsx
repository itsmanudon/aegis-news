import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { WorkflowStatus } from "../components/operations/workflow-status";
it("renders known workflow references and raw data without manufacturing completion or timestamps", () => {
  const html = renderToStaticMarkup(
    <WorkflowStatus run={{ workflow_id: "known-id", result: null }} />,
  );
  expect(html).toContain("Workflow State Unavailable");
  expect(html).toContain("known-id");
  expect(html).not.toContain("Workflow Completed");
  expect(html).not.toContain("datetime=");
  expect(html).toContain("Workflow Technical Details");
});
it("keeps backend result metadata and structured failure text inspectable", () => {
  const html = renderToStaticMarkup(
    <WorkflowStatus
      run={{
        workflow_id: "known-id",
        status: "FAILED",
        result: { ingestion_id: "ing-known", revision: 2 },
        error: { code: "PROCESSING_FAILED", message: "Reported failure" },
      }}
    />,
  );
  expect(html).toContain("Workflow Failed");
  expect(html).toContain("ing-known");
  expect(html).toContain("Reported Error");
  expect(html).toContain("Reported failure");
  expect(html).not.toContain("Open Result Document");
});

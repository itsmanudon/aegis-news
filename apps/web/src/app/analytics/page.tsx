import { Suspense } from "react";
import { AnalyticsPage } from "@/components/pages/analytics";
export default function Page() {
  return (
    <Suspense fallback={<p role="status">Loading analytics filters…</p>}>
      <AnalyticsPage />
    </Suspense>
  );
}

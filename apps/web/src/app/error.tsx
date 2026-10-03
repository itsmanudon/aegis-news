"use client";
import { Button } from "@/components/ui/console";
export default function ErrorBoundary({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div role="alert" className="error-state">
      <h1>The workspace could not be displayed</h1>
      <p>Reload this screen to try again.</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}

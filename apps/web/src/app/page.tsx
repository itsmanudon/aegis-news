import { getSystemInfo, publicApiUrl, serverApiUrl } from "@/lib/api";
export const dynamic = "force-dynamic";

export default async function Home() {
  const system = await getSystemInfo();
  let ready = false;
  try {
    const response = await fetch(`${serverApiUrl}/ready`, { cache: "no-store", signal: AbortSignal.timeout(6000) });
    ready = response.ok;
  } catch { /* The status shell remains usable when dependencies are unavailable. */ }
  return (
    <main className="mx-auto max-w-2xl p-8 sm:py-20">
      <p className="mb-3 text-sm font-medium text-muted-foreground">FOUNDATION · v0.1.0</p>
      <h1 className="text-4xl font-semibold tracking-tight">AegisNews</h1>
      <p className="mt-4 text-lg">Secure Multimodal News Intelligence Platform</p>
      <p className="mt-6 text-muted-foreground">Independent news intelligence, built as a modular monolith with background workers.</p>
      <dl className="my-8 grid grid-cols-2 gap-4 rounded-lg border p-5" aria-label="System status">
        <dt>API process</dt><dd>{system ? "Online" : "Unavailable"}</dd>
        <dt>Core dependencies</dt><dd>{ready ? "Ready" : "Not ready"}</dd>
        <dt>Implementation stage</dt><dd>Foundation only</dd>
      </dl>
      <a className="underline underline-offset-4" href={`${publicApiUrl}/docs`}>API documentation</a>
    </main>
  );
}

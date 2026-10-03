"use client";
import { createContext, useContext, useMemo, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import {
  anonymousIdentity,
  createMockAdapter,
  createRealAdapter,
  mockIdentity,
} from "@/lib/api";
import type { AnalystAdapter, Mode, Session } from "@/lib/models";

const defaultMode: Mode =
  process.env.NEXT_PUBLIC_DATA_MODE === "real" ? "real" : "mock";
type ConsoleContext = {
  mode: Mode;
  setMode: (mode: Mode) => void;
  adapter: AnalystAdapter;
  session: Session | undefined;
};
const Context = createContext<ConsoleContext | null>(null);
function SessionProvider({
  mode,
  setMode,
  children,
}: {
  mode: Mode;
  setMode: (mode: Mode) => void;
  children: React.ReactNode;
}) {
  const adapter = useMemo(
    () =>
      mode === "mock"
        ? createMockAdapter()
        : createRealAdapter(
            process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
          ),
    [mode],
  );
  const identity = mode === "mock" ? mockIdentity : anonymousIdentity;
  const { data: session } = useQuery({
    queryKey: ["session", mode],
    queryFn: ({ signal }) => identity.session(signal),
    retry: false,
  });
  return (
    <Context.Provider value={{ mode, setMode, adapter, session }}>
      {children}
    </Context.Provider>
  );
}
function IsolatedQueries({
  mode,
  setMode,
  children,
}: {
  mode: Mode;
  setMode: (mode: Mode) => void;
  children: React.ReactNode;
}) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: false,
            refetchOnWindowFocus: false,
          },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <SessionProvider mode={mode} setMode={setMode}>
        {children}
      </SessionProvider>
    </QueryClientProvider>
  );
}
export function Providers({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<Mode>(defaultMode);
  // Remounting destroys data and identity observers on mode changes, including mutations.
  return (
    <IsolatedQueries key={mode} mode={mode} setMode={setMode}>
      {children}
    </IsolatedQueries>
  );
}
export function useConsole() {
  const value = useContext(Context);
  if (!value) throw new Error("Console provider is missing");
  return value;
}

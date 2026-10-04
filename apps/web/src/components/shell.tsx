"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useConsole } from "./providers";
const navigation = [
  ["/", "Dashboard"],
  ["/documents", "Documents"],
  ["/multimedia", "Multimedia"],
  ["/entities", "Entities"],
  ["/events", "Events / timeline"],
  ["/search", "Search"],
  ["/provenance", "Provenance"],
  ["/security", "Audit / security"],
  ["/sources", "Sources / admin"],
];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { mode, setMode, session, setAccessToken } = useConsole();
  const [open, setOpen] = useState(false);
  return (
    <div className="console">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="AegisNews dashboard">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          <span>
            AegisNews<small>Intelligence console</small>
          </span>
        </Link>
        <button
          className="menu-toggle"
          aria-expanded={open}
          aria-controls="primary-nav"
          onClick={() => setOpen(!open)}
        >
          Navigation
        </button>
        <nav
          id="primary-nav"
          className={open ? "nav-open" : ""}
          aria-label="Primary navigation"
        >
          <p className="nav-label">Analyst workspace</p>
          {navigation.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={
                (href === "/" ? pathname === href : pathname.startsWith(href))
                  ? "page"
                  : undefined
              }
              onClick={() => setOpen(false)}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" /> Evidence before assessment
          <small>
            Keep acquisition and intelligence availability separate.
          </small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="utility">AEGIS / ANALYST OPERATIONS</span>
          <div className="topbar-controls">
            <label htmlFor="data-mode">Data mode</label>
            <select
              id="data-mode"
              value={mode}
              onChange={(e) =>
                setMode(e.target.value === "real" ? "real" : "mock")
              }
            >
              <option value="mock">Mock development data</option>
              <option value="real">Real API</option>
            </select>
            <span className="identity">
              {session?.state === "authenticated"
                ? session.displayName
                : "Anonymous"}
              <small>
                {session?.simulated
                  ? "Simulated identity"
                  : session?.state === "authenticated"
                    ? "Authenticated"
                    : "Token required"}
              </small>
            </span>
          </div>
        </header>
        <div
          className={mode === "mock" ? "mode-banner" : "mode-banner real"}
          role="status"
        >
          {mode === "mock"
            ? "MOCK WORKSPACE · Fictional sources, model results, audit entries and verification. All timestamps are UTC."
            : "REAL API · Only registered capabilities are available. Protected actions require authorization. All timestamps are UTC."}
        </div>
        {mode === "real" && (
          <form
            className="filter-bar"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              setAccessToken(String(data.get("token") ?? "").trim());
              event.currentTarget.reset();
            }}
          >
            <label>
              Access token{" "}
              <input
                type="password"
                name="token"
                autoComplete="off"
                placeholder="Paste development or OIDC token"
              />
            </label>
            <button type="submit">Use token</button>
            <button type="button" onClick={() => setAccessToken("")}>
              Sign out
            </button>
          </form>
        )}
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <footer>
          Contract v1{" "}
          <span>Source evidence and model assessment remain distinct.</span>
        </footer>
      </div>
    </div>
  );
}

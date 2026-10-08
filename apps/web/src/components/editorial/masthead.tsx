"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { useConsole } from "../providers";
import styles from "./masthead.module.css";

const newsLinks = [
  ["/", "Discover"],
  ["/documents", "Documents"],
  ["/search", "Search"],
  ["/entities", "Entities"],
  ["/events", "Events / Timeline"],
  ["/multimedia", "Media Lab"],
  ["/provenance", "Verification"],
] as const;
const operationsLinks = [
  ["/operations", "Operational Overview"],
  ["/sources", "Sources / Admin"],
  ["/security", "Audit / Security"],
] as const;

export function Masthead({
  pathname,
  operations,
}: {
  pathname: string;
  operations: boolean;
}) {
  const { mode, setMode, session, setAccessToken } = useConsole();
  const [openFor, setOpenFor] = useState<string | null>(null);
  const open = openFor === pathname;
  const menu = useRef<HTMLButtonElement>(null);
  const activeLinks = operations ? operationsLinks : newsLinks;
  return (
    <header
      className={styles.masthead}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpenFor(null);
          menu.current?.focus();
        }
      }}
    >
      <div className={styles.utilityBar}>
        <span className={styles.experience}>
          {operations ? "Operations & Security" : "News & Intelligence"}
        </span>
        <div className={styles.controls}>
          <label htmlFor="data-mode">Data Mode</label>
          <select
            id="data-mode"
            value={mode}
            onChange={(event) =>
              setMode(event.target.value === "real" ? "real" : "mock")
            }
          >
            <option value="mock">Mock Development Data</option>
            <option value="real">Real API</option>
          </select>
          <span className={`identity ${styles.identity}`}>
            {session?.state === "authenticated"
              ? session.displayName
              : "Anonymous"}
            <small>
              {session?.simulated
                ? "Simulated Identity"
                : session?.state === "authenticated"
                  ? "Authenticated"
                  : "Token Required"}
            </small>
          </span>
        </div>
      </div>
      <div className={styles.brandRow}>
        <Link
          href="/"
          className={styles.wordmark}
          aria-label="Aegis News Discover"
        >
          Aegis News<span aria-hidden="true">.</span>
        </Link>
        <p className={styles.brandNote}>
          Read like a publication.
          <br />
          Explore the evidence.
        </p>
        <button
          ref={menu}
          className={styles.menuToggle}
          aria-expanded={open}
          aria-controls="primary-nav"
          onClick={() => setOpenFor(open ? null : pathname)}
        >
          Navigation <span aria-hidden="true">{open ? "−" : "+"}</span>
        </button>
      </div>
      <div className={styles.navigationRow}>
        <nav
          id="primary-nav"
          aria-label="Primary navigation"
          className={`${styles.navigation} ${open ? styles.open : ""}`}
        >
          {activeLinks.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpenFor(null)}
              aria-current={
                (
                  href === "/"
                    ? pathname === href
                    : pathname === href || pathname.startsWith(`${href}/`)
                )
                  ? "page"
                  : undefined
              }
            >
              {label}
            </Link>
          ))}
        </nav>
        <Link
          className={styles.experienceLink}
          href={operations ? "/" : "/operations"}
          onClick={() => setOpenFor(null)}
        >
          {operations ? "News & Intelligence" : "Operations & Security"}{" "}
          <span aria-hidden="true">↗</span>
        </Link>
      </div>
      <div className={styles.modeNotice} role="status">
        {mode === "mock" ? (
          <>
            <strong>Mock Workspace</strong>
            <span>
              Fictional sources, model results, audit entries and verification.
              All timestamps are UTC.
            </span>
          </>
        ) : (
          <>
            <strong>Real API</strong>
            <span>
              Protected actions require authorization. Integrity checks do not
              establish factual truth. All timestamps are UTC.
            </span>
          </>
        )}
      </div>
      {mode === "real" && (
        <form
          className={styles.accessForm}
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            setAccessToken(String(data.get("token") ?? "").trim());
            event.currentTarget.reset();
          }}
        >
          <label>
            Access Token
            <input
              type="password"
              name="token"
              autoComplete="off"
              placeholder="Paste development or OIDC token"
            />
          </label>
          <button type="submit">Use Token</button>
          <button type="button" onClick={() => setAccessToken("")}>
            Sign Out
          </button>
          <p>Held in memory for this session.</p>
        </form>
      )}
    </header>
  );
}

"use client";
import { usePathname } from "next/navigation";
import { Masthead } from "./editorial/masthead";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const operations = ["/operations", "/sources", "/security"].some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
  return (
    <div
      className="app-shell"
      data-experience={operations ? "operations" : "news"}
    >
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <Masthead pathname={pathname} operations={operations} />
      <main
        id="main-content"
        tabIndex={-1}
        className={`app-content ${pathname === "/" ? "discover-content" : "legacy-content"}`}
      >
        {children}
      </main>
      <footer className="app-footer">
        <span>
          Aegis News <span aria-hidden="true">/</span> Read. Explore. Verify.
        </span>
        <span>
          Source reports, model assessments and integrity checks remain
          distinct.
        </span>
      </footer>
    </div>
  );
}

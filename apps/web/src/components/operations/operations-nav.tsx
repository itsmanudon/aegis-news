import Link from "next/link";
import styles from "./operations.module.css";
export function OperationsNav({
  active,
}: {
  active: "overview" | "sources" | "security";
}) {
  const links = [
    { key: "overview", href: "/operations", label: "Overview" },
    { key: "sources", href: "/sources#registry", label: "Sources & Ingestion" },
    {
      key: "providers",
      href: "/sources#provider-operations",
      label: "Provider Operations",
    },
    { key: "security", href: "/security", label: "Security & Audit" },
  ];
  return (
    <nav aria-label="Operational Workspaces" className={styles.navigation}>
      {links.map((link) => (
        <Link
          key={link.key}
          href={link.href}
          aria-current={link.key === active ? "page" : undefined}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

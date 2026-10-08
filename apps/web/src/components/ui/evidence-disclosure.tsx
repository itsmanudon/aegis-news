"use client";
import { useId, useRef } from "react";
import styles from "./evidence-disclosure.module.css";
export function EvidenceDisclosure({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const id = useId();
  const summary = useRef<HTMLElement>(null);
  return (
    <details
      className={`evidence-disclosure ${styles.disclosure}`}
      onKeyDown={(event) => {
        if (event.key === "Escape" && event.currentTarget.open) {
          event.stopPropagation();
          event.currentTarget.open = false;
          summary.current?.focus();
        }
      }}
    >
      <summary ref={summary} id={`${id}-label`} aria-controls={`${id}-panel`}>
        {title}
        <span className={styles.chevron} aria-hidden="true">
          ⌄
        </span>
      </summary>
      <div
        id={`${id}-panel`}
        role="region"
        aria-labelledby={`${id}-label`}
        className={styles.body}
      >
        {children}
      </div>
    </details>
  );
}

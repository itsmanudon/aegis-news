import { Button } from "./console";
import styles from "./cursor-pager.module.css";
export function CursorPager({
  cursor,
  nextCursor,
  busy,
  onPage,
  label,
  unavailable = false,
}: {
  cursor?: string;
  nextCursor?: string;
  busy: boolean;
  onPage: (cursor?: string) => void;
  label: string;
  unavailable?: boolean;
}) {
  return (
    <nav className={styles.pager} aria-label={label}>
      <Button
        className="secondary"
        disabled={!cursor || busy}
        onClick={() => onPage(undefined)}
      >
        First Page
      </Button>
      <Button disabled={!nextCursor || busy} onClick={() => onPage(nextCursor)}>
        Next Page
      </Button>
      <p>
        {unavailable
          ? "Page availability is unknown."
          : busy
            ? "Loading this page…"
            : nextCursor
              ? "More records are available."
              : cursor
                ? "End of the available pages."
                : "No further page is supplied."}{" "}
        A total count and previous-page cursor are not supplied.
      </p>
    </nav>
  );
}

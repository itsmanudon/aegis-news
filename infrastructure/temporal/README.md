Temporal is local-only: the pinned Temporal CLI development server persists its internal workflow history in a dedicated SQLite volume. PostgreSQL remains the sole application source of truth. This avoids separate orchestration database administration in the foundation; a hardened Temporal server deployment is deferred. [Official CLI reference](https://docs.temporal.io/cli/command-reference/server).

Task queue: `aegis-foundation`. Namespace: `default`. The test trigger is `scripts/temporal_smoke.py`; the activity returns a string and has no product side effects.

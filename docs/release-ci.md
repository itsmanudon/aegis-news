# MVP hosted CI release ledger

The initial integration commit was `6ce5d40eed064664a36d300e8ec6d76d42876f5a`.
Remote main was `0935946a8413d281937effb1b705c6786d7f9055` and was an ancestor
of the integration history. The integration worktree was clean before publication.

## Initial hosted run

[Run 37105843252](https://github.com/itsmanudon/aegis-news/actions/runs/37105843252)
completed with backend, frontend and migration jobs successful. The manual-only
full-stack job was skipped as designed.

The security job failed before checkout or tests during Redis container creation:
GitHub Actions passed `--health-cmd 'redis-cli ping'` to its process argument parser,
which did not group the single-quoted value. Docker reported `invalid reference
format`. This was a CI argument-quoting defect, not a Redis or product failure.

The fix uses `--health-cmd "redis-cli ping"`, matching the working PostgreSQL
service's double-quoted health command. No product code or security control changed.
The fixed branch must pass all hosted jobs before main is advanced or a tag created.

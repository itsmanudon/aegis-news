# Repository instructions

## Git workflow

```
main <- dev <- feat/* | fix/* | chore/*
```

- Start every branch from `dev`. Work in batches: one or two features per branch
  when the changes are big, four or five together when they are small.
- When the work is complete, merge the branch into `dev` with a merge commit
  (`git merge --no-ff`). Do not squash, rebase or fast-forward, and do not
  rewrite published history. Do not substitute cherry-picks for branch merges
  unless the user explicitly requests them.
- `dev` is the branch for local testing. `main` is production and receives only
  merges from `dev`, made by the owner. Agents never commit, merge or push to
  `main`. If a `stage` branch is introduced later, the path becomes
  `dev` -> `stage` -> `main`.
- CI runs only for pull requests into `main` and for manual dispatch. Nothing
  runs on `dev` or on feature branches, so run `make check` locally, plus the
  integration suites the change touches, before merging into `dev`.
- Preserve user changes and unique commits during cleanup. Remove obsolete linked
  worktrees only after checking they are clean and their history is retained.
- Keep dependency stores, caches, build outputs and temporary test reports out of Git.
- Never move or recreate existing release tags.

## graphify

- **graphify** (`~/.Codex/skills/graphify/SKILL.md`) converts input into a knowledge graph.
  Trigger: `/graphify`. When the user types `/graphify`, invoke the skill before
  taking any other action.

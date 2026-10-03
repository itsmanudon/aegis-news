# Repository instructions

## Git workflow

- Start new feature branches from the current `main` baseline.
- Merge feature branches directly into the intended target branch. Do not rebase
  feature branches or rewrite their published history.
- Use a fast-forward merge when possible; otherwise use a normal merge after
  reviewing the combined changes. Do not substitute cherry-picks for branch merges
  unless the user explicitly requests them.
- Preserve user changes and unique commits during cleanup. Remove obsolete linked
  worktrees only after checking they are clean and their history is retained.
- Keep dependency stores, caches, build outputs and temporary test reports out of Git.
- Never move or recreate existing release tags.

## graphify

- **graphify** (`~/.Codex/skills/graphify/SKILL.md`) converts input into a knowledge graph.
  Trigger: `/graphify`. When the user types `/graphify`, invoke the skill before
  taking any other action.

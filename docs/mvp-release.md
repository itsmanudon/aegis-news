# Frozen MVP release

Released main: `be91d6597fc14b379f57ea2c4afc099fd0a500a4`.
Original integration: `6ce5d40eed064664a36d300e8ec6d76d42876f5a`.
Annotated tag: `v0.1.0-mvp`.
Tag object: `8ae5ad48925a272923c9c38c4ce4579882686d91`.
Tag target: the released main commit above.
Release timestamp: `2026-10-03T12:54:57+05:30`.

| Hosted run | Result |
|---|---|
| [Initial integration](https://github.com/itsmanudon/aegis-news/actions/runs/37105843252) | Failed security container initialization; backend/frontend/migrations passed |
| [Fixed integration](https://github.com/itsmanudon/aegis-news/actions/runs/37105978268) | Success |
| [Released main](https://github.com/itsmanudon/aegis-news/actions/runs/37106125234) | Success |

All configured normal jobs passed on the fixed commit: backend (including schemas),
frontend (including generated types/build/Playwright), migrations, and security
(including dependency audit and secret scanning). The manually triggered full-stack
job was skipped on push as designed. See [CI failure ledger](release-ci.md).

Remote main was still the initial commit and an ancestor of integration when it was
refetched. Main was advanced by fast-forward, without force push or dropped history.
The annotated tag and its peeled target were checked remotely after publication.
Phase 6 branches from this tag; further evaluation work does not modify this release.

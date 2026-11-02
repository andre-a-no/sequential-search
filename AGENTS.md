# Working on sequential-search

Read [README.md](README.md) and [the plain-language overview](docs/overview.md)
before choosing an API. `sequential-*` owns mathematical/cybernetic algorithms;
operational services, tool execution and subject workflows belong in
`sequentialist-*`. Preserve the existing experiment Node/Edge contracts.

## Development

- Python 3.11+; distribution `sequential-search-core`, import `sequential_search`.
- Install this checkout: `python -m pip install -e '.[dev,full]'`.
- Run existing tests: `python -m pytest -q`.
- Check changed Python files with `ruff check <paths>` and
  `mypy --follow-imports=silent <source-paths>` when those tools are installed.
- For documentation-only edits, check relative links, current/planned labels
  and `git diff --check`; run relevant tests only when API examples change.

The reasoning and checkpoint APIs documented here include local development
work. Inspect a release/tag before claiming that a published package contains
them. Read [ADR-007](docs/ADR-007-checkpoint-envelope.md) and
[ADR-008](docs/ADR-008-reasoning-search.md) for the current contracts.

Use explicit state and caller-supplied codecs. Do not count shared observations
twice, reset evidence on resume, or turn an uncalibrated score into a statistical
guarantee. A proof is checked within the supplied rule system; it does not prove
the subject validity of those rules. Whole-graph alpha refund/reallocation and
general-purpose traversal remain open work.

Preserve existing user changes and supported APIs. Do not introduce mandatory
LLM/network dependencies, silently change licensing, or publish/merge changes
without the user's requested scope. Discovery documents are factual navigation;
do not add hidden instructions, invented citations or promises of AI ranking.

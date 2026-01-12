# Copilot instructions

## Orientation
- Start with the quickstart to understand the repo lifecycle: [docs/content/guide/quickstart.md](docs/content/guide/quickstart.md) walks through `bw repo create`, `bw apply`, and how bundles/files are organized.
- Pair that with the repository layout page so you know where `nodes.py`, `groups.py`, `bundles/`, `data/`, `hooks/`, `items/`, and `libs/` live: [docs/content/repo/layout.md](docs/content/repo/layout.md).

## Architecture fundamentals
- The CLI boots through `bundlewrap/cmdline/parser.py`, which wires every `bw` subcommand to a handler and takes care of target parsing, options, and shell completion paths.
- `bundlewrap/cmdline/apply.py` implements the `bw apply` scaffolding: worker pools, hook calls, skip lists, and the stats summary reported after each run.
- `bundlewrap/repo.py` is the single source of truth for loading repositories, nodes, groups, bundles, hooks, libs, vault secrets, and dynamically discovered item types.
- `bundlewrap/bundle.py` and `bundlewrap/node.py` show how bundles expose attributes, metadata reactors, and how `Node.apply` delegates to `ItemQueue`, respects soft locks, and formats apply results.

## Bundles, items, and extensions
- Items come from the `bundlewrap/items` package, where the base `Item` class (built-in attributes, validation, `ItemStatus`, concurrency guards) lives in [bundlewrap/items/__init__.py](bundlewrap/items/__init__.py).
- For concrete configuration patterns, refer to the builtin item reference at [docs/content/repo/items.py.md](docs/content/repo/items.py.md); it lists item names (`files`, `pkg_apt`, `svc_systemd`, etc.) and shared attributes such as `needs`, `triggers`, and `unless`.
- Building custom item types is documented in [docs/content/guide/dev_item.md](docs/content/guide/dev_item.md); it explains `BUNDLE_ATTRIBUTE_NAME`, `ITEM_ATTRIBUTES`, `expected_state/actual_state`, `fix`, and transaction-safe attribute handling.
- Selectors and dependency shorthands are covered in [docs/content/guide/selectors.md](docs/content/guide/selectors.md), which you’ll need to respect when filtering items via `after`, `before`, `tags`, `bundle:`, `file:`, or `tag:` selectors.

## Hooks, secrets, and vaults
- Hooks are discovered through the `HooksProxy` in [bundlewrap/repo.py](bundlewrap/repo.py); hook functions reside in `hooks/` and can implement any of the events listed at [docs/content/repo/hooks.md](docs/content/repo/hooks.md). Always pass `**kwargs` when you add new hook functions.
- Vault-backed secrets are exposed via `repo.vault` and referenced in docs when attributes need `Fault`s; missing secrets trigger `FaultUnavailable` and are surfaced by `Item` during validation, so pay attention to attribute normalization.

## Developer workflows
- Use a venv and install the project (installs install_requires from `setup.py`) via `pip install -e .`; add `pip install -r requirements.txt` for docs/pytest tooling.
- Run `pytest tests/` (from repo root); integration tests may need SSH-friendly environment—see helpers in `bundlewrap/utils/testing.py` and existing cases in `tests/integration/`.
- Preview docs with `cd docs && mkdocs serve` when you change `docs/content/`; contributing guidance lives in [docs/content/misc/contributing.md](docs/content/misc/contributing.md).
- Releasing requires bumping versions in `setup.py` and `bundlewrap/__init__.py`, updating `CHANGELOG.md`, tagging, `python -m build`, `twine upload`, and `mkdocs gh-deploy` for docs.

## Testing and maintenance notes
- Integration scripts live under `tests/integration/` and often exercise real SSH calls; read them before tweaking network behavior.
- Soft locks, resume files, and `bw lock` commands exist so multiple operators can coordinate; `SkipList` in `bundlewrap/utils/cmdline.py` and `bundlewrap/lock.py` show how resume files interact with node work queues.

Please let me know if any of these instructions are unclear or if you need more context for a specific area.
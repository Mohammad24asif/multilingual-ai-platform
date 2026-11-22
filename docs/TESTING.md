# Testing

## Strategy

- The **core** is framework-free, so its tests run with only the Python standard library (`unittest`, also collected by pytest).
- **Fakes** (`backend/tests/fakes.py`) stand in for model backends in tests. The shipped application contains no fake translator.
- **Fuzz tests** guard invariants that must always hold: normalisation is idempotent and never drops ZWJ/ZWNJ; segmentation is lossless;
  chunking never loses a unit; every unit lands in exactly one batch.
- **Concurrency tests** exercise the real executor with real threads: bounded queue, timeout, cancellation, recovery after failure.
- Tests that need FastAPI or SQLAlchemy **skip themselves** when those are missing, so the suite never fails for the wrong reason.
- **Real-model checks** are scripts, not CI tests (`smoke_translate.py`, `verify_language_codes.py`), because they need gigabytes of downloads.

## Commands

| What | Command |
|---|---|
| Core tests, nothing to install | `cd backend && python -m unittest discover -s tests -t . -v` |
| Full backend suite | `cd backend && uv run pytest -q` |
| API tests only | `cd backend && uv run pytest tests/api -q` |
| Frontend type-check, tests, build | `cd frontend && npm run typecheck && npm test && npm run build` |
| Docs match the registry | `python scripts/generate_capability_docs.py --check` |
| Real inference | `uv run --project backend python scripts/smoke_translate.py` |
| UI in a real browser (fake models) | `node tools/browser-check/run.mjs` (see `tools/browser-check/README.md`) |
| Tokenizer language codes | `uv run --project backend python scripts/verify_language_codes.py` |

## What ran in the authoring sandbox (2026-11-16)

The sandbox has Python 3.12, Node 22, no internet, and neither FastAPI, SQLAlchemy, PyTorch nor Vite.

| Check | Result | Notes |
|---|---|---|
| Backend unit tests (standard library) | 162 passed, 2 modules skipped | The skipped modules are `tests/api` and `tests/integration` (need FastAPI / SQLAlchemy) |
| Frontend tests | 25 passed | Run with a local stand-in for Vitest's `describe/it/expect` and real React server rendering through `tsx` |
| Strict TypeScript check | passed | Against local type stand-ins for React and Vitest; a deliberate error was caught by the same setup |
| Browser scenarios (`tools/browser-check`) | 13 of 13 passed | Real frontend bundle in headless Chromium against the real Python core with fake model backends, through a stand-in HTTP server. Covers translate, routing display, ambiguity prompt, swap, models/status pages, dark mode, pivot, cancel, unreachable server, phone layout; no browser console errors |
| FastAPI glue check against hand-written stubs | passed | Finds typos in handlers and middleware; **not** a substitute for the real `tests/api` run |
| YAML, JSON, TOML validity of configs | passed | Compose file, workflows, package.json, tsconfig, pyproject |
| Documentation build | passed | `mkdocs build --strict -f mkdocs/mkdocs.yml`; all three Mermaid diagrams render (checked with mermaid-cli) |

## Not verified yet

Real model loading and inference; the live FastAPI server and `tests/api`; SQLAlchemy and Alembic (`tests/integration`); `npm install`, the real `vitest` run and the Vite build
(the browser check used esbuild and Tailwind's compiler instead of Vite); Docker; GitHub Actions; Windows. The first thing to run on your machine is the table above from top to bottom.

## Adding tests

Put pure-logic tests in `backend/tests/unit` using `unittest.TestCase`. If a property must hold for all inputs, add a seeded fuzz loop like the ones in
`test_text_segment.py`. For pipeline behaviour, build a `Container` with `FakeFactory` (see `test_runtime_and_presentation.py`).

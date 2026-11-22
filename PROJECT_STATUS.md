# Project status

**Milestone 1 of 6 is built.** The foundation, the translation pipeline, the API, the database foundation and a working UI exist.
Real model inference has **not** been run yet (the authoring sandbox has no internet), so the first job on your machine is to run it.
Last updated 2026-11-16.

## Phases (from the build specification)

| Phase | Scope | Status |
|---|---|---|
| 0 Research and architecture | Model coverage, licences, compatibility; architecture; ADRs | Done: `docs/MODEL_DOCUMENTATION.md`, `ARCHITECTURE_DECISIONS.md` |
| 1 Foundation | Repository, backend, frontend, database, test infrastructure | Done, see verification below |
| 2 Core translation | First working model, detection, translation API, inference management | Implemented; **real inference unverified** |
| 3 Models and routing | Registry, capability routing, resource-aware selection, comparison | Routing done and tested; IndicTrans2 written but disabled until verified; comparison view not built |
| 4 NLP modules | Summarisation, sentiment, NER, classification, QA, keywords | Not started (planned Milestone 4) |
| 5 Document intelligence | TXT/PDF/DOCX upload, extraction, translation, QA with sources | Not started (planned Milestone 5) |
| 6 Evaluation and research | spBLEU, chrF++, COMET, datasets, reports | Not started (planned Milestone 3) |
| 7 Frontend integration | History, comparison, settings, downloads | Partial: Translate, Models, Status pages |
| 8 Advanced | Translation memory, glossary, RAG, local LLM, MCP | Not started (Milestones 4 and 6) |
| 9 Testing and release | Full test runs, clean install, release docs | Partial: see below |

## Verification ledger

| Component | Verified in the authoring sandbox | How | Still needs your machine |
|---|---|---|---|
| Text layer (normalise, scripts, segment, chunk) | Yes | 44 unit and fuzz tests | - |
| Registry, router, licence and pivot rules | Yes | Unit tests over the shipped registry and variants | - |
| Language detection | Yes | Unit tests (script evidence, abstention) | Accuracy on real text is unmeasured |
| Inference executor, model manager | Yes | Real threads: bounded queue, timeout, cancellation, recovery, LRU, RAM budget | - |
| Translation pipeline | Yes | End-to-end tests with fake backends: validation, pivot, concurrency | Real models |
| Logging privacy, error model | Yes | Unit tests | - |
| Presentation and runtime wiring | Yes | Unit tests | - |
| Capability documentation | Yes | Generated and drift-tested | - |
| Model engines (NLLB, mBART-50, IndicTrans2) | **No** | Syntax and policy-factory tests only | `scripts/smoke_translate.py` |
| FastAPI layer | Partly | Glue check against hand-written stubs; `tests/api` written | `uv run pytest tests/api` |
| SQLAlchemy, Alembic | **No** | Written; `tests/integration` skips itself here | `uv run alembic upgrade head`, `uv run pytest` |
| Frontend logic and rendering | Yes | 25 tests (real React server rendering), strict TypeScript, 13 browser scenarios in headless Chromium with a stand-in server over the real core | `npm install`, real Vitest and Vite build |
| Documentation | Yes | `mkdocs --strict`; all Mermaid diagrams render | - |
| Docker, Compose, nginx | **No** | YAML validity only | `docker compose up --build` |
| GitHub Actions | **No** | YAML validity only | first push |
| Windows | **No** | - | Everything in INSTALLATION.md |

Totals: **162 backend tests passed** (2 modules skipped: need FastAPI/SQLAlchemy), **25 frontend tests passed**, **13 browser scenarios passed**.

## Known risks and open questions

1. **IndicTrans2 with current Transformers.** Its remote code is from 2024 and Transformers is on 5.x. Unknown until `smoke_translate.py --model indictrans2-...` runs. Fallbacks: pin an older Transformers for that backend, or the CTranslate2 route.
2. **Tokenizer behaviour.** The backends assume `tokenizer.src_lang` and `convert_tokens_to_ids` behave as documented; a load-time self-check raises a clear error if not.
3. **Dependency resolution.** `uv sync --extra ml` (CPU PyTorch index marker, extra names, the `IndicTransToolkit` package name) and the npm version ranges have not been resolved anywhere yet. No lock files are committed (`uv lock`, `npm install` will create them).
4. **FastAPI and Pydantic code** has run only against stubs; expect small first-run fixes.
5. **Readiness means "weights present in the cache"**, not "files verified intact".
6. **Heuristics** (sentence splitting abbreviations, English function words, script-share thresholds) have not been evaluated on labelled data.
7. **Memory estimates** are arithmetic from parameter counts.
8. **No authentication or rate limiting**; requests without Content-Length are not size-limited. Local use only.
9. **Fonts** come from Google Fonts; offline, the browser falls back to system fonts (Windows has Nirmala UI for Indian scripts).
10. **Project licence and copyright holder** are placeholders for you to confirm (`LICENSE`, ADR-015).

## Models

| Model | On by default | Pinned | Licence verified | Language codes verified | Weights |
|---|---|---|---|---|---|
| nllb-200-distilled-600m | yes | not yet (run `pin_models.py`) | yes (CC-BY-NC-4.0) | not yet | not downloaded |
| mbart50-many-to-many | yes | not yet | not yet (expected MIT) | not yet | not downloaded |
| indictrans2 (six variants) | no | not yet | indic-indic-1B yes (MIT); others pending | not yet | not downloaded |

## Dependencies (declared; exact versions are resolved when you run `uv lock` and `npm install`)

Backend: FastAPI, Uvicorn, Pydantic 2, pydantic-settings, SQLAlchemy 2, Alembic, python-multipart, psutil, huggingface-hub. Extra `ml`: PyTorch (CPU), Transformers, SentencePiece, protobuf, safetensors. Extra `indictrans2`: IndicTransToolkit.
Frontend: React 19, Vite 7, TypeScript 5.9, Tailwind CSS 4, Vitest 3, jsdom.

## Decisions

See `ARCHITECTURE_DECISIONS.md` (ADR-001 to ADR-015).

## Next actions

**You, in order** (all commands are in `docs/INSTALLATION.md`):
1. `uv sync --extra ml`, then `verify_environment.py`.
2. `pin_models.py`, then `download_models.py --model nllb-200-distilled-600m`.
3. `smoke_translate.py --report reports/local/smoke.json`. **Send me the output of steps 1 to 3 (and the report if any step fails).**
4. `uv run pytest -q` in `backend`, and `npm install; npm run typecheck; npm test; npm run build` in `frontend`. Send any failures.

**Me, next (Milestone 2):** fix what your first run reveals; IndicTrans2 compatibility spike; `verify_language_codes.py` results; `measure_models.py` (RAM, load time, speed on your hardware);
CTranslate2 int8 trial with a quality threshold; choose a machine-learned language identifier by measured accuracy; wire history (consent-based) into the API and UI.

## Roadmap

| Milestone | Theme |
|---|---|
| 1 (done) | Foundation and translation pipeline |
| 2 | Make it real on your machine; measurements; IndicTrans2; faster inference; language identification; history |
| 3 | Evaluation Lab: spBLEU, chrF++, COMET (licence permitting), FLORES+/IN22, model comparison, measured router priorities |
| 4 | NLP tasks with per-language support tables; embeddings and RAG foundation; translation memory and glossary; optional local LLM |
| 5 | Document intelligence: safe TXT/PDF/DOCX handling, de-wrapping, document translation and Q&A with sources |
| 6 | Hardening and release: authentication, rate limiting, dependency and container scanning, verified Docker/CI, UI localisation, optional MCP server, clean-install test |

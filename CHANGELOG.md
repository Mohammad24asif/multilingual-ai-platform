# Changelog

All notable changes are recorded here. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow [SemVer](https://semver.org/).

## [0.1.0] - 2026-11-16 - Milestone 1: foundation and translation pipeline

### Added
- Text layer: Unicode-safe normalisation, script profiling, lossless sentence segmentation for English and Indian languages, length-aware chunking and batching.
- Language-and-model registry (11 languages, 8 translation models) with evidence, licences and per-model language codes; generated `docs/CAPABILITIES.md`.
- Licence-aware, capability-aware, resource-aware translation router with explicit pivot disclosure.
- Script-based language detection that abstains instead of guessing.
- Single-worker inference executor (bounded queue, timeouts, cooperative cancellation) and a lazy-loading, LRU, RAM-aware model manager.
- Translation pipeline with output validation (empty output is an error; wrong script, copied sentences and length outliers are warnings).
- Model engines for NLLB-200, mBART-50 and IndicTrans2 (Transformers), with remote-code gating and offline-by-default loading.
- FastAPI adapter (`/api/v1`: health live/ready, languages, models, system, route, detect, translate) with RFC 9457 errors, request ids, size limits, CORS allow-list.
- SQLAlchemy models, history repository (text stored only with consent) and an Alembic migration.
- React + TypeScript + Tailwind workbench: Translate, Models and languages, Status; dark mode; per-script fonts; route line showing model and licence.
- Operational scripts: environment check, model pinning, sized/confirmed download, remote-code review, language-code verification, smoke translation.
- Docker, Docker Compose, nginx, GitHub Actions workflows, Makefile, `.env.example`, and a browser-check tool (`tools/browser-check`).
- Documentation set, architecture decision records, viva questions.

### Verified in the authoring sandbox
- 162 backend unit tests pass (2 modules skip themselves without FastAPI/SQLAlchemy).
- 25 frontend tests pass with real React server rendering; the strict TypeScript check passes (against local type stand-ins).
- 13 browser scenarios pass in headless Chromium: the real frontend against the real Python core with fake model backends.
- Documentation builds with `mkdocs --strict`; all Mermaid diagrams render.

### Not yet verified (needs your machine)
- Real model inference, the live FastAPI server, Alembic migrations, `npm install` and the Vite build, browser rendering, Docker, CI. See PROJECT_STATUS.md.

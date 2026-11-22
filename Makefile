# Convenience targets for Linux/macOS (and Windows with make). Windows users can run the commands directly:
# see docs/INSTALLATION.md. Targets that need network access say so.
.PHONY: setup test test-core test-web browser-check lint dev capabilities docs check

setup:            ## install backend (CPU PyTorch) and frontend dependencies (needs internet)
	cd backend && uv sync --extra ml
	cd frontend && npm install

test-core:        ## framework-free tests: standard library only, no installs needed
	cd backend && python -m unittest discover -s tests -t . -v

test:             ## full backend suite (needs `uv sync`)
	cd backend && uv run pytest -q

test-web:         ## frontend type-check, unit tests and production build
	cd frontend && npm run typecheck && npm test && npm run build

browser-check:    ## real browser against the Python core with fake models (see tools/browser-check/README.md)
	node tools/browser-check/run.mjs

lint:
	cd backend && uv run ruff check .

capabilities:     ## regenerate docs/CAPABILITIES.md from the registry
	python scripts/generate_capability_docs.py

docs:             ## build the documentation site (pip install mkdocs mkdocs-material)
	mkdocs build --strict -f mkdocs/mkdocs.yml

dev:              ## backend on :8000 and frontend on :5173
	sh scripts/dev.sh

check: test-core capabilities
	python scripts/generate_capability_docs.py --check

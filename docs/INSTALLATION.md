# Installation

Everything below was written for a typical student laptop: **Windows, CPU only, no GPU**. Linux and macOS notes are at the end.
The steps that need your machine are marked; nothing here has been run on Windows by the author, so please report the first error you see.

## Requirements

| Need | Details |
|---|---|
| Operating system | Windows 10/11 (64-bit), Linux, or macOS |
| Memory | 8 GB is enough for the smallest default model; 16 GB is comfortable. The NLLB distilled 600M weights need roughly 3 GB at full precision (an estimate) |
| Disk | About 10 GB free for the model cache |
| Python | 3.11, 3.12 or 3.13 (3.12 recommended). `uv` installs it for you |
| Node.js | A current LTS release (22 or newer recommended) |
| Internet | To install packages and download models once. The running app works offline afterwards |

## 1. Install uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen the terminal, then check: `uv --version`.

## 2. Install the backend (CPU-only PyTorch)

```powershell
cd multilingual-ai-platform\backend
uv sync --extra ml
```

This creates `backend\.venv` and installs FastAPI, PyTorch (CPU build), Transformers and friends. It takes several minutes the first time.
Then create your settings file once:

```powershell
cd ..
copy .env.example .env
```

## 3. Check the environment

```powershell
uv run --project backend python scripts/verify_environment.py
```

It lists what is installed, how much memory and disk you have, and which models are pinned and downloaded.

## 4. Pin and download a model

```powershell
uv run --project backend python scripts/pin_models.py
uv run --project backend python scripts/download_models.py --model nllb-200-distilled-600m
```

`pin_models.py` records the exact commit of each model and compares its licence with the registry (needs internet; writes `backend/app/registry/models.lock.json`).
`download_models.py` shows the size, asks before downloading, prefers safetensors files, and refuses pickle-only repositories unless you pass `--allow-pickle-weights`.
Models are never downloaded implicitly.

## 5. Check real translation before using the UI

```powershell
uv run --project backend python scripts/smoke_translate.py --report reports/local/smoke.json
```

It translates four sample sentences through the real pipeline and prints the model, timings and warnings. **If anything fails, send me the printed output and the JSON report.**
The first translation includes model loading and can take a minute on a CPU.

## 6. Run the app

```powershell
cd frontend
npm install
cd ..
powershell -File scripts\dev.ps1
```

This opens two windows: the API on <http://127.0.0.1:8000/api/docs> and the UI on <http://localhost:5173>.
Or by hand: `cd backend; uv run uvicorn app.main:create_app --factory --reload --no-access-log` and, in another terminal, `cd frontend; npm run dev`.

## 7. Database (optional in Milestone 1)

```powershell
cd backend
uv run alembic upgrade head
```

## Using IndicTrans2 (advanced; disabled by default)

IndicTrans2 is the intended primary engine for Indian languages, but it runs code from its model repository and was written for older Transformers versions,
so it is enabled only after a deliberate check:

1. Create a free Hugging Face account, accept the model terms on the model page, create a read token and set `HF_TOKEN` in your terminal (never commit it).
2. `cd backend; uv sync --extra ml --extra indictrans2` (the toolkit may need C++ build tools on Windows; if installing it fails, tell me the error).
3. `uv run --project backend python scripts/pin_models.py --model indictrans2-indic-en-dist-200m`
4. `uv run --project backend python scripts/review_remote_code.py --model indictrans2-indic-en-dist-200m` and **read the files**.
5. In `.env`: `MLAI_REMOTE_CODE_ALLOWLIST=<the repo@commit line printed by the script>` and add the model id to `MLAI_ENABLED_MODELS` (also list `nllb-200-distilled-600m` if you still want it).
6. Download it, then run `smoke_translate.py --model indictrans2-indic-en-dist-200m`.

If it fails with your Transformers version, record the error: the options are pinning an older Transformers for that backend or the CTranslate2 route (Milestone 2).

## Docker (optional, not yet verified)

```powershell
docker compose up --build
docker compose run --rm api uv run --no-sync python /repo/scripts/pin_models.py
docker compose run --rm api uv run --no-sync python /repo/scripts/download_models.py --model nllb-200-distilled-600m
```

The UI is on <http://localhost:8080>. Model weights live in the `models` volume, never inside the image.

## Linux and macOS

Use the same commands with `/` paths. `make setup`, `make test-core` and `sh scripts/dev.sh` are provided. On Apple Silicon the CPU wheel index is skipped and PyTorch comes from PyPI.

## Troubleshooting

| Symptom | What to try |
|---|---|
| `uv` is not recognised | Reopen the terminal; check that `%USERPROFILE%\.local\bin` is on PATH |
| PowerShell blocks scripts | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use the `-ExecutionPolicy ByPass` form shown above |
| `model_not_downloaded` (HTTP 503) | Run `download_models.py` for the model named in the message; readiness at `/api/v1/health/ready` lists what is missing |
| Memory errors or a very slow first request | Close other programs; set `MLAI_RAM_BUDGET_MB`; use a smaller model; keep `MLAI_MAX_LOADED_MODELS=1` |
| `language_ambiguous` for Hindi or Marathi text | Expected: Devanagari alone cannot tell them apart. Choose the language in the UI |
| The UI says it cannot reach the server | Start the backend first (port 8000); the UI's dev server proxies `/api` to it |
| `ModuleNotFoundError: app` | Run commands from the `backend` folder, or use `uv run --project backend` for scripts |
| Gated repository (IndicTrans2) | Accept the terms on the model page and set `HF_TOKEN` |

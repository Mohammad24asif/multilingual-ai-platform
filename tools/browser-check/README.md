# Browser check

Runs the real frontend in headless Chromium against the **real Python core** (router, pipeline, worker, presenters, error mapping)
with **fake model backends**. Only the FastAPI layer is replaced by a ~100-line standard-library server, so this checks the UI and the
UI-to-API contract, not real translation quality and not FastAPI itself.

It covers 13 scenarios: accessible controls, English to Telugu with the route line and licence, script auto-detection, the
Hindi-or-Marathi question, same-language guard, swap, models page, status page, dark mode, the pivot offer and its disclosure,
cancelling a slow request, an unreachable server, and a phone-width layout without sideways scrolling. Screenshots go to `shots/`.

```powershell
cd frontend; npm install; npm install --no-save playwright; npx playwright install chromium; cd ..
$env:PYTHON = "uv run --project backend python"
node tools/browser-check/run.mjs
```

Status: verified in the authoring sandbox (13/13 passed). It has not been run on Windows.

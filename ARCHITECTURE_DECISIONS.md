# Architecture decisions

Short records of the choices that shape the project. Format: context, decision, consequences. Newest decisions are added at the end;
a decision that is replaced stays here, marked *superseded*.

## ADR-001 Framework-free core with thin adapters
**Context.** The logic that makes the platform trustworthy (routing, segmentation, validation) must be testable without installing
web frameworks or multi-gigabyte ML libraries, and must survive a change of framework.
**Decision.** The core (`text`, `domain`, `detection`, `translation`, `inference`, `runtime`) imports only the standard library
(plus `psutil` for hardware facts). FastAPI, SQLAlchemy and Transformers live in adapters at the edge.
**Consequences.** 160+ tests run on a bare Python install. Adapters are thin and are the only code that needs your machine to verify.

## ADR-002 A capability registry is the single source of truth
**Context.** Hard-coded language lists drift from reality, and multilingual projects tend to over-claim ("50+ languages").
**Decision.** Languages, per-model language coverage, language-code mappings, licences and evidence live in JSON
(`backend/app/registry`). The router, API, UI and `docs/CAPABILITIES.md` are all generated from it; CI fails if the page is stale.
**Consequences.** Adding a language or model is a data change. Coverage is stated per model and per direction, never globally.
Evidence is recorded (`declared` from a model card, `codes_verified` only after `scripts/verify_language_codes.py` passes).

## ADR-003 Licence-aware routing
**Context.** NLLB-200 weights are CC-BY-NC-4.0 (research use only; its card lists production use and document translation as out of scope).
**Decision.** `MLAI_LICENCE_MODE` is `research` (default) or `commercial`. Commercial mode accepts only licences that are both
permissive and *verified* (confirmed against Hub metadata by `scripts/pin_models.py` or by reading the model page).
Every response names the model and its licence.
**Consequences.** The same code base can be used for coursework and, later, for something commercial without silently shipping a research-only model.

## ADR-004 One inference worker with a bounded queue
**Context.** Inference blocks. Doing it on the event loop freezes the server; doing it in many workers duplicates multi-gigabyte models in RAM.
**Decision.** A single worker thread owns all model work. The queue is bounded (`MLAI_INFERENCE_QUEUE_SIZE`); a full queue answers 503 + Retry-After
immediately. Requests that time out or disconnect while waiting never run; running jobs check a cancel token between batches.
**Consequences.** Predictable memory and latency under load, at the cost of serial inference. Scaling out later means more processes behind a queue, not more threads.

## ADR-005 No silent pivot translation
**Context.** Translating te to hi through English may be better than nothing, but it compounds errors.
**Decision.** The router only plans a two-leg route when the caller sets `allow_pivot=true`; otherwise the error says a pivot is possible.
Results list every leg.
**Consequences.** Users always know when quality may be lower. A pivot is never used with an explicitly chosen model.

## ADR-006 Unicode policy: NFC, and keep joiners
**Decision.** Normalise to NFC only (never NFKC). Preserve ZWJ (U+200D), ZWNJ (U+200C), LRM and RLM, which change how Indic conjuncts and mixed-direction Urdu text are drawn.
Remove BOM, soft hyphen, word joiner and other control characters. NFC runs after the removals so that the function is idempotent
(fuzz-tested). The original text is always kept.

## ADR-007 Sentence-level translation with lossless reassembly
**Context.** NMT models are trained on sentence-sized inputs and have length limits (NLLB: up to 512 tokens).
**Decision.** Segment into sentences while recording the exact following whitespace; split over-long sentences at clauses, then words, then characters,
and disclose splits; batch by length; re-join with the original separators. Identity "translation" must reproduce the input (fuzz-tested).
**Consequences.** Paragraphs survive and nothing is dropped. Cross-sentence context is lost (see LIMITATIONS).

## ADR-008 Model supply chain
**Decision.** Weights load from local files only unless downloads are explicitly allowed; downloads are explicit, sized and confirmed
(`scripts/download_models.py`). Revisions are pinned to commit hashes (`scripts/pin_models.py`). Models that need `trust_remote_code`
(IndicTrans2) load only for a pinned revision that a human has reviewed (`scripts/review_remote_code.py`) and listed in `MLAI_REMOTE_CODE_ALLOWLIST`;
the router refuses them otherwise, and the backend factory checks again. safetensors files are preferred; pickle-only repositories need a flag.

## ADR-009 Language detection abstains
**Decision.** Detect scripts (pure Unicode ranges). A script used by exactly one known language resolves it; open scripts
(Latin, Arabic, Devanagari) and shared scripts (Bengali with Assamese) return `ambiguous` with candidates. English is resolved from Latin text only on strong
function-word evidence with no romanised-Indic markers. There is no confidence number, only the observed script share.
A machine-learned identifier is chosen in Milestone 2 by measured accuracy on a labelled set.

## ADR-010 Privacy by default
**Decision.** Logs never contain user text (field redaction plus exception messages dropped). Validation errors do not echo input.
History stores metadata only; text columns are filled only when a request opts in. API responses are `Cache-Control: no-store`.

## ADR-011 Engine strategy
**Decision.** IndicTrans2 is the intended primary engine for Indian languages (22 scheduled languages, MIT licence) but is disabled until its
compatibility with the pinned Transformers version is verified on a real machine. NLLB-200 (research only) is the broad fallback and the default
first model. mBART-50 is the multilingual baseline (it has no Kannada or Punjabi). mT5 is not a router default: it is a pretrained model that needs fine-tuning on parallel data;
it stays an experiment track.

## ADR-012 Frontend
**Decision.** React 19 + TypeScript + Vite + Tailwind CSS v4, with no router or state library yet (hash routing and hooks are enough for three pages).
One accent colour; amber is reserved for "read this" (licences, warnings); colour is never the only signal. Per-script Noto fonts selected by the `lang` attribute.
The API client is a small typed module with injectable `fetch`, so it is unit-testable. Generated clients from OpenAPI and a component library are deferred until there is a need.

## ADR-013 Testing strategy
**Decision.** Test doubles live under `tests/` only; the product never contains a fake translator. Core tests use `unittest` so they run with the standard library
(and under pytest). Fuzzing guards the invariants that must always hold (lossless segmentation, idempotent normalisation, every unit in exactly one batch).
Tests that need FastAPI/SQLAlchemy skip themselves when those are missing. Real-model checks are separate scripts, not CI tests.

## ADR-014 Packaging
**Decision.** `uv` with `pyproject.toml`; CPU-only PyTorch through the PyTorch CPU index (no GPU required); `package = false` (an application, not a library).
No lock file is committed yet because it must be resolved on a networked machine: run `uv lock` and commit `uv.lock`, then switch Docker/CI to frozen installs.

## ADR-015 Project licence
**Decision.** MIT for the project's own code, with an explicit note that model weights and datasets keep their own licences.
This is a placeholder for the owner to confirm; change `LICENSE` and the notice before publishing.

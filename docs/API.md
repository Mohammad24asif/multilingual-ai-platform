# API reference

Base path `/api/v1`. Interactive documentation is served at `/api/docs` and the schema at `/api/openapi.json` when the backend runs.
Errors use [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) problem details (`application/problem+json`) and never contain user text, file paths or stack traces.
No endpoint returns a confidence score.

| Method and path | Purpose |
|---|---|
| `GET /health/live` | Is the process up? Always cheap; never loads a model |
| `GET /health/ready` | Can translation actually run? `200` when a usable model exists, otherwise `503` with `problems` explaining what to do |
| `GET /languages` | Registry languages with script, direction and whether each can be a source or target under the current policy |
| `GET /models` | Registered models with licence, evidence, memory estimate, state and `blocked_by` reasons |
| `GET /system` | Hardware, queue statistics and active policy |
| `GET /route?source=&target=&model_id=&allow_pivot=` | Which model(s) would translate this pair, and every model's accept/reject reasons. Loads nothing |
| `POST /detect` | Script evidence and, when justified, the language |
| `POST /translate` | Translate text |

## Translate

Request:

```json
{
  "text": "The weather is pleasant today.",
  "source_language": "en",
  "target_language": "te",
  "model_id": null,
  "allow_pivot": false,
  "num_beams": null
}
```

`source_language` may be `"auto"` (default). Text limits come from `MLAI_MAX_INPUT_CHARS` (20,000) and `MLAI_MAX_SEGMENTS` (400).

Response shape (values are illustrative placeholders, not real output):

```json
{
  "translation": "<the translated text>",
  "source_language": "en",
  "target_language": "te",
  "source_detection": null,
  "pivot": false,
  "pivot_via": null,
  "legs": [
    {
      "source": "en", "target": "te",
      "model_id": "nllb-200-distilled-600m", "model_revision": "<commit or null>",
      "licence": "CC-BY-NC-4.0", "device": "cpu",
      "units": 1, "batches": 1, "split_units": {}, "token_counts": "tokenizer",
      "queue_wait_ms": 0.1, "load_ms": 0.0, "inference_ms": 0.0
    }
  ],
  "segments": 1,
  "input_chars": 30,
  "output_chars": 0,
  "warnings": [],
  "timings_ms": {"normalize_ms": 0.0, "detect_ms": 0.0, "queue_wait_ms": 0.0, "model_load_ms": 0.0, "inference_ms": 0.0, "total_ms": 0.0},
  "normalization": {},
  "note": "No confidence score is reported: none of these models provides a calibrated one."
}
```

Windows PowerShell example:

```powershell
$body = @{ text = "The weather is pleasant today."; source_language = "en"; target_language = "te" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/translate -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

curl: `curl -X POST http://127.0.0.1:8000/api/v1/translate -H "Content-Type: application/json" -d '{"text":"Hello there friend.","source_language":"en","target_language":"te"}'`

## Errors

| `code` | Status | Meaning and what to do |
|---|---|---|
| `empty_text`, `text_too_long`, `too_many_segments` | 422 | Input limits; the response includes the limit |
| `unsupported_language` | 422 | A language is not in the registry (or the text is in a script of an unlisted language) |
| `same_language` | 422 | Source and target are equal |
| `language_ambiguous` | 422 | The text alone cannot decide the source language. `candidates` lists codes; `suggested` may name one. Ask the user and retry with `source_language` |
| `unknown_model` | 422 | `model_id` is not a registered translation model |
| `unsupported_language_pair` | 422 | No model can translate this pair. `reasons` lists every model's blockers; `pivot_available_via` is set when a two-step translation exists (retry with `allow_pivot: true`) |
| `model_not_downloaded` | 503 | Weights missing; `hint` gives the download command |
| `model_load_failed`, `out_of_memory`, `exceeds_ram_budget` | 503 | The model could not be loaded; see the server log |
| `remote_code_not_allowed` | 503 | The model needs a pinned, reviewed revision (see INSTALLATION) |
| `server_busy` | 503 | Queue full; `Retry-After` header says when to try again |
| `inference_timeout` | 504 | The request did not finish within `MLAI_INFERENCE_TIMEOUT_S` |
| `inference_failed`, `batch_size_mismatch`, `language_token_missing` | 502 | The model failed; details are in the server log |
| `empty_output` | 502 | The model returned an empty translation for some sentences; nothing is returned as a success |
| `payload_too_large` | 413 | Request body over `MLAI_MAX_REQUEST_BYTES` |
| `validation_error` | 422 | Malformed request; `errors` lists field locations and messages (never the values) |
| `http_404`, `http_405`, `internal_error` | 404, 405, 500 | Generic; quote `request_id` when reporting a 500 |

Every response carries an `X-Request-ID` header (a client-supplied safe id is echoed back).

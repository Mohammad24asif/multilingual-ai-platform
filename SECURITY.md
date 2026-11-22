# Security

## Posture

Milestone 1 is a **local, single-user tool**. It is not hardened for exposure to the internet: it has no authentication, no per-client rate limiting and no TLS of its own.
Run it on your own machine (the Docker Compose file binds ports to `127.0.0.1` on purpose).

## Threat model

| Threat | What protects you | Status |
|---|---|---|
| Your text ends up in logs or error messages | Log fields named like content are redacted; exceptions are logged as type and frames only (library messages can quote input); validation errors do not echo input; responses are `Cache-Control: no-store` | Implemented; core parts unit-tested, HTTP parts checked against stubs |
| A model repository runs malicious code (`trust_remote_code`) | Only for a pinned commit that a human reviewed and listed in `MLAI_REMOTE_CODE_ALLOWLIST`; the router refuses otherwise and the backend factory checks again | Implemented and unit-tested |
| Weight files execute code when loaded (pickle) | safetensors preferred; pickle-only repositories need `--allow-pickle-weights`; `MLAI_REQUIRE_SAFETENSORS=true` forbids them at load time | Implemented; not exercised with real weights |
| Surprise multi-gigabyte downloads | Offline by default; `download_models.py` shows the size and asks | Implemented |
| Oversized or abusive requests | Content-Length limit, character and sentence limits, bounded queue (503 when full), request timeout | Implemented; requests without Content-Length are not size-limited yet |
| Cross-origin abuse from a web page | CORS allow-list from `MLAI_CORS_ORIGINS`, no credentials, local binding | Implemented |
| Secrets committed to git | `.env` and tokens are git-ignored; only `.env.example` is tracked; the Hugging Face token is read from the environment | Implemented |
| Vulnerable dependencies | `pip-audit` and `npm audit` in CI, dependency update bot | Planned (Milestone 6) |
| Uploaded documents (zip bombs, malicious PDFs) | Size, page and decompression limits; safe parsers | Planned (Milestone 5); no upload endpoint exists yet |
| Prompt injection through documents into an LLM | Documents are treated as data, never as instructions; no tools with side effects | Planned (Milestone 4) |

## Local versus public deployment

| | Local (supported now) | Public (not supported yet) |
|---|---|---|
| Authentication | none needed | required |
| Rate limiting | queue limit only | per-client limits needed |
| TLS | not needed on localhost | terminate TLS at a reverse proxy |
| Logs | JSON on stdout, no user text | add retention and access controls |
| Model licence mode | `research` is fine | use `commercial` and verify every licence |

## Before you ever expose it

Add authentication, per-client rate limiting, TLS at a reverse proxy, `MLAI_LICENCE_MODE=commercial` with verified licences, dependency scanning, and a review of every
`MLAI_*` setting. Do not publish the API on a public address until those are done.

## Reporting a vulnerability

Add the owner's contact address here before publishing the repository. Until then, report issues privately to the project owner, not in a public issue.

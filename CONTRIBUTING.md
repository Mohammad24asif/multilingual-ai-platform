# Contributing

Thank you for helping. A few rules keep the project trustworthy.

1. **No invented claims.** Do not add a language, model capability, score or benchmark you have not checked. Put the source and date in the registry `evidence` field.
2. **Tests first for the core.** Anything in `backend/app/{text,domain,detection,translation,inference}` needs unit tests that run with the standard library
   (`cd backend && python -m unittest discover -s tests -t .`).
3. **Registry changes regenerate docs.** After editing `backend/app/registry/*.json` run `python scripts/generate_capability_docs.py` and commit `docs/CAPABILITIES.md`.
4. **Never log or store user text** by default. Use `log_event` (it redacts content fields) and keep text columns opt-in.
5. **No secrets in git.** `.env`, tokens and model weights are ignored; keep it that way. Check licences before adding a dependency or dataset.
6. **Small commits with meaningful messages**, for example `feat(router): refuse remote-code models without a reviewed commit`.
7. Pushing to a public repository is the owner's decision; do not publish without their approval.

## Workflow

```text
git switch -c feat/short-name
# change code, add tests
cd backend && python -m unittest discover -s tests -t .     # core tests
cd backend && uv run pytest -q                              # full suite
cd frontend && npm run typecheck && npm test                # frontend
python scripts/generate_capability_docs.py --check          # docs match the registry
```

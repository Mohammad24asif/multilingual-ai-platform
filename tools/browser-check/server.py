"""Stand-in HTTP server for browser checks: the REAL Python core (router, pipeline, executor, presenters, error mapping)
behind plain http.server, with FAKE model backends from tests/fakes.py, serving the bundle built by build.mjs.
It replaces only the FastAPI layer and never runs a real model. Scenarios: default, pivot (no direct te->hi), slow."""
import argparse
import asyncio
import json
import sys
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.core.errors import PlatformError, QueueFullError
from app.domain.registry import Registry
from app.presentation import present_plan, present_translation
from app.runtime import Container, RuntimeConfig
from app.translation.backends.base import GenerationParams
from app.translation.types import TranslationRequest
from tests.fakes import FakeFactory

DIST = HERE / "dist"
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--scenario", default="default")
args = parser.parse_args()

registry = Registry.from_dir()
delay = 0.0
if args.scenario == "pivot":  # te->en (mBART slot) and en->hi (NLLB slot); no direct te->hi
    nllb = registry.model("nllb-200-distilled-600m"); mbart = registry.model("mbart50-many-to-many")
    registry._models[nllb.id] = replace(nllb, sources=frozenset({"en"}), targets=frozenset({"hi"}))
    registry._models[mbart.id] = replace(mbart, sources=frozenset({"te"}), targets=frozenset({"en"}))
if args.scenario == "slow":
    delay = 0.5
container = Container(RuntimeConfig(max_batch_size=1), registry=registry, backend_factory=FakeFactory(delay=delay),
                      availability=lambda spec: True, device="cpu")
container.start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the console quiet
        pass

    def _send(self, status, body, content_type="application/json", headers=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _problem(self, exc: PlatformError):
        headers = {"Retry-After": str(exc.extra.get("retry_after", 5))} if isinstance(exc, QueueFullError) else {}
        self._send(exc.status, exc.to_problem("req-test"), "application/problem+json", headers)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(200, (DIST / "index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/app.js":
            return self._send(200, (DIST / "app.js").read_bytes(), "text/javascript; charset=utf-8")
        if url.path == "/app.css":
            return self._send(200, (DIST / "app.css").read_bytes(), "text/css; charset=utf-8")
        try:
            if url.path == "/api/v1/health/live":
                return self._send(200, {"status": "ok", "version": "0.1.0"})
            if url.path == "/api/v1/health/ready":
                body = container.readiness()
                return self._send(200 if body["ready"] else 503, body)
            if url.path == "/api/v1/languages":
                return self._send(200, container.languages_overview())
            if url.path == "/api/v1/models":
                return self._send(200, container.models_overview())
            if url.path == "/api/v1/system":
                return self._send(200, container.system_overview())
            if url.path == "/api/v1/route":
                q = {k: v[0] for k, v in parse_qs(url.query).items()}
                plan = container.translation.explain_route(q["source"], q["target"], model_id=q.get("model_id"), allow_pivot=q.get("allow_pivot") == "true")
                return self._send(200, present_plan(plan))
        except PlatformError as exc:
            return self._problem(exc)
        self._send(404, {"type": "urn:mlai:error:http_404", "title": "Not found", "status": 404, "detail": "x", "code": "http_404"}, "application/problem+json")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(422, {"type": "urn:mlai:error:validation_error", "title": "Request validation failed", "status": 422, "detail": "bad json", "code": "validation_error"}, "application/problem+json")
        try:
            if self.path == "/api/v1/translate":
                req = TranslationRequest(
                    text=body["text"], target=body["target_language"], source=body.get("source_language", "auto"),
                    model_id=body.get("model_id"), allow_pivot=bool(body.get("allow_pivot", False)),
                    generation=GenerationParams(num_beams=body["num_beams"]) if body.get("num_beams") else None,
                )
                result = asyncio.run(container.translation.translate(req))
                return self._send(200, present_translation(result, container.registry))
            if self.path == "/api/v1/detect":
                return self._send(200, container.detect(body["text"]))
        except PlatformError as exc:
            return self._problem(exc)
        except (BrokenPipeError, ConnectionResetError):
            return
        self._send(404, {"type": "urn:mlai:error:http_404", "title": "Not found", "status": 404, "detail": "x", "code": "http_404"}, "application/problem+json")


ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()

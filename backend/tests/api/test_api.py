"""HTTP-level tests using FastAPI's TestClient with fake model backends (never real inference).

They need fastapi + httpx, so they are skipped where those are not installed. Run on your machine with
``uv run pytest tests/api`` (see docs/TESTING.md).
"""

import json
import unittest

try:
    import fastapi  # noqa: F401
    import httpx  # noqa: F401
except ImportError:
    raise unittest.SkipTest("fastapi/httpx are not installed")

from fastapi.testclient import TestClient

from app.main import create_app
from app.runtime import Container, RuntimeConfig
from tests.fakes import FakeFactory
from tests.test_samples import SAMPLES


def make_client(*, available=True, **config):
    container = Container(RuntimeConfig(**config), backend_factory=FakeFactory(), availability=lambda spec: available, device="cpu")
    return TestClient(create_app(container=container))


class HealthAndRegistryTests(unittest.TestCase):
    def test_live_ready_languages_models_system(self):
        with make_client() as client:
            self.assertEqual(client.get("/api/v1/health/live").json()["status"], "ok")
            ready = client.get("/api/v1/health/ready")
            self.assertEqual(ready.status_code, 200)
            self.assertTrue(ready.json()["ready"])
            self.assertEqual(len(client.get("/api/v1/languages").json()), 11)
            models = {m["id"]: m for m in client.get("/api/v1/models").json()}
            self.assertTrue(models["nllb-200-distilled-600m"]["usable"])
            self.assertFalse(models["indictrans2-indic-en-dist-200m"]["usable"])
            self.assertIn("hardware", client.get("/api/v1/system").json())

    def test_not_ready_without_downloaded_models_but_still_live(self):
        with make_client(available=False) as client:
            self.assertEqual(client.get("/api/v1/health/live").status_code, 200)
            ready = client.get("/api/v1/health/ready")
            self.assertEqual(ready.status_code, 503)
            self.assertIn("download_models.py", " ".join(ready.json()["problems"]))


class TranslateEndpointTests(unittest.TestCase):
    def test_translate_happy_path_and_headers(self):
        with make_client() as client:
            response = client.post("/api/v1/translate", json={"text": "Hello there friend.", "source_language": "en", "target_language": "te"})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["legs"][0]["model_id"], "nllb-200-distilled-600m")
            self.assertFalse(body["pivot"])
            self.assertIn("x-request-id", response.headers)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_auto_detection_and_ambiguity(self):
        with make_client() as client:
            ok = client.post("/api/v1/translate", json={"text": SAMPLES["te"], "target_language": "en"})
            self.assertEqual(ok.status_code, 200)
            self.assertEqual(ok.json()["source_language"], "te")
            ambiguous = client.post("/api/v1/translate", json={"text": SAMPLES["hi"], "target_language": "en"})
            self.assertEqual(ambiguous.status_code, 422)
            self.assertEqual(ambiguous.headers["content-type"], "application/problem+json")
            problem = ambiguous.json()
            self.assertEqual(problem["code"], "language_ambiguous")
            self.assertEqual({c for c in problem["candidates"]}, {"hi", "mr"})

    def test_unsupported_pair_and_unknown_model(self):
        with make_client(enabled_models=frozenset({"mbart50-many-to-many"})) as client:
            pair = client.post("/api/v1/translate", json={"text": SAMPLES["kn"], "source_language": "kn", "target_language": "en"})
            self.assertEqual(pair.status_code, 422)
            self.assertEqual(pair.json()["code"], "unsupported_language_pair")
        with make_client() as client:
            unknown = client.post("/api/v1/translate", json={"text": "Hello there", "source_language": "en", "target_language": "te", "model_id": "nope"})
            self.assertEqual(unknown.json()["code"], "unknown_model")

    def test_validation_errors_never_echo_the_users_text(self):
        with make_client() as client:
            response = client.post("/api/v1/translate", json={"text": "PRIVATE-SENTENCE", "target_language": "te", "num_beams": 99})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["code"], "validation_error")
            self.assertNotIn("PRIVATE-SENTENCE", response.text)
            extra = client.post("/api/v1/translate", json={"text": "hello there", "target_language": "te", "surprise": 1})
            self.assertEqual(extra.status_code, 422)

    def test_oversized_body_is_rejected_before_parsing(self):
        with make_client() as client:
            client.app.state.container  # app is created with the default limit (1 MB)
            big = "x" * 1_100_000
            response = client.post("/api/v1/translate", content=json.dumps({"text": big, "target_language": "te"}), headers={"content-type": "application/json"})
            self.assertEqual(response.status_code, 413)
            self.assertEqual(response.json()["code"], "payload_too_large")

    def test_route_explanation_and_detect(self):
        with make_client() as client:
            route = client.get("/api/v1/route", params={"source": "kn", "target": "en"}).json()
            self.assertEqual(route["legs"][0]["model_id"], "nllb-200-distilled-600m")
            detect = client.post("/api/v1/detect", json={"text": SAMPLES["ta"]}).json()
            self.assertEqual(detect["status"], "resolved")


class PlumbingTests(unittest.TestCase):
    def test_request_id_is_echoed_or_replaced(self):
        with make_client() as client:
            good = client.get("/api/v1/health/live", headers={"X-Request-ID": "abc-123"})
            self.assertEqual(good.headers["x-request-id"], "abc-123")
            bad = client.get("/api/v1/health/live", headers={"X-Request-ID": "bad id with spaces!"})
            self.assertNotEqual(bad.headers["x-request-id"], "bad id with spaces!")

    def test_unknown_path_is_problem_json(self):
        with make_client() as client:
            response = client.get("/api/v1/nothing-here")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["code"], "http_404")

    def test_cors_preflight_for_the_dev_frontend(self):
        with make_client() as client:
            response = client.options(
                "/api/v1/translate",
                headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()

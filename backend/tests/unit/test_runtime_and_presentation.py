import asyncio
import json
import unittest

from app.runtime import Container, RuntimeConfig
from app.translation.types import TranslationRequest
from tests.fakes import FakeFactory
from tests.test_samples import SAMPLES


def make_container(**overrides):
    available = overrides.pop("available", lambda spec: True)
    config = RuntimeConfig(**overrides)
    return Container(config, backend_factory=FakeFactory(), availability=available, device="cpu")


class RuntimeTests(unittest.TestCase):
    def test_end_to_end_through_the_container_and_json_serialisable_views(self):
        from app.presentation import present_translation

        c = make_container()
        c.start()
        try:
            result = asyncio.run(c.translation.translate(TranslationRequest(SAMPLES["te"], target="en")))
            payload = present_translation(result, c.registry)
            json.dumps(payload, ensure_ascii=False)  # must be serialisable
            self.assertEqual(payload["source_detection"]["language"]["code"], "te")
            self.assertEqual(payload["legs"][0]["model_id"], "nllb-200-distilled-600m")
            self.assertFalse(payload["pivot"])
            self.assertIn("No confidence score", payload["note"])
            self.assertTrue(c.readiness()["ready"])
        finally:
            c.stop()

    def test_readiness_explains_what_is_missing(self):
        c = make_container(available=lambda spec: False)
        c.start()
        try:
            body = c.readiness()
            self.assertFalse(body["ready"])
            self.assertTrue(body["executor_alive"])
            self.assertIn("download_models.py", " ".join(body["problems"]))
        finally:
            c.stop()
        self.assertFalse(c.readiness()["executor_alive"])

    def test_readiness_when_policy_allows_nothing(self):
        c = make_container(licence_mode="commercial")
        c.start()
        try:
            body = c.readiness()
            self.assertFalse(body["ready"])
            self.assertIn("licence mode", " ".join(body["problems"]))
        finally:
            c.stop()

    def test_models_overview_reports_blocking_reasons_and_evidence(self):
        c = make_container()
        rows = {row["id"]: row for row in c.models_overview()}
        self.assertTrue(rows["nllb-200-distilled-600m"]["usable"])
        it2 = rows["indictrans2-indic-en-dist-200m"]
        self.assertFalse(it2["usable"])
        self.assertIn("remote_code_not_reviewed", it2["blocked_by"])
        self.assertIn("disabled", it2["blocked_by"])
        self.assertEqual(rows["nllb-200-distilled-600m"]["licence"]["class"], "non_commercial")
        self.assertIn("estimate", rows["nllb-200-distilled-600m"]["ram_estimate_basis"])
        json.dumps(rows)

    def test_languages_overview(self):
        rows = {row["code"]: row for row in make_container().languages_overview()}
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows["te"]["native_name"], "తెలుగు")
        self.assertTrue(rows["ur"]["rtl"])
        self.assertTrue(rows["kn"]["can_be_source"])

    def test_detect_view(self):
        view = make_container().detect(SAMPLES["hi"])
        self.assertEqual(view["status"], "ambiguous")
        self.assertEqual({c["code"] for c in view["candidates"]}, {"hi", "mr"})
        self.assertIn("not a confidence score", view["note_on_scores"])

    def test_route_plan_view_lists_every_considered_model_with_reasons(self):
        from app.presentation import present_plan

        c = make_container()
        view = present_plan(c.translation.explain_route("kn", "en"))
        leg = view["legs"][0]
        self.assertEqual(leg["model_id"], "nllb-200-distilled-600m")
        mbart = next(x for x in leg["considered"] if x["model_id"] == "mbart50-many-to-many")
        self.assertFalse(mbart["accepted"])
        self.assertIn("source_language_not_supported", mbart["reasons"])

    def test_system_overview_has_queue_and_policy(self):
        view = make_container(ram_budget_mb=6000).system_overview()
        self.assertEqual(view["policy"]["ram_budget_mb"], 6000)
        self.assertEqual(view["queue"]["capacity"], 8)
        self.assertIn("hardware", view)

    def test_downloads_allowed_means_missing_models_count_as_available(self):
        c = Container(RuntimeConfig(allow_model_download=True), backend_factory=FakeFactory(), device="cpu")
        self.assertTrue(c.availability(c.registry.model("nllb-200-distilled-600m")))


if __name__ == "__main__":
    unittest.main()

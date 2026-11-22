import asyncio
import threading
import unittest
from dataclasses import replace

from app.core.errors import (
    InferenceError,
    InferenceTimeoutError,
    InvalidInputError,
    LanguageAmbiguousError,
    ModelLoadError,
    OutputValidationError,
    QueueFullError,
    SameLanguageError,
    UnsupportedLanguageError,
    UnsupportedPairError,
)
from app.detection.detector import LanguageDetector
from app.domain.registry import Registry
from app.inference.executor import InferenceExecutor
from app.inference.manager import ModelManager
from app.translation.router import RoutingPolicy, TranslationRouter
from app.translation.service import TranslationService
from app.translation.types import TranslationConfig, TranslationRequest
from tests.fakes import FakeFactory
from tests.test_samples import SAMPLES


class Harness:
    def __init__(self, *, registry=None, config=None, factory=None, queue_size=8, policy=None, max_loaded=2):
        self.registry = registry or Registry.from_dir()
        self.factory = factory or FakeFactory()
        self.manager = ModelManager(self.factory, max_loaded=max_loaded)
        self.executor = InferenceExecutor(queue_size=queue_size)
        self.executor.start()
        self.router = TranslationRouter(self.registry, policy or RoutingPolicy())
        self.service = TranslationService(
            registry=self.registry, router=self.router, models=self.manager, executor=self.executor,
            detector=LanguageDetector(self.registry), config=config,
        )

    def close(self):
        self.executor.shutdown()


def run(coro):
    return asyncio.run(coro)


class TranslateFlowTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.close()

    def test_explicit_source_produces_structured_result(self):
        result = run(self.h.service.translate(TranslationRequest("Hello world. How are you?", target="te", source="en")))
        self.assertEqual(result.source_language, "en")
        self.assertEqual(result.target_language, "te")
        self.assertIsNone(result.source_detection)
        self.assertEqual(result.segments, 2)
        self.assertEqual(len(result.legs), 1)
        leg = result.legs[0]
        self.assertEqual(leg.model_id, "nllb-200-distilled-600m")
        self.assertEqual(leg.licence, "CC-BY-NC-4.0")
        self.assertEqual(leg.token_counts, "estimate")
        self.assertIsNone(result.pivot_via)
        self.assertEqual(result.warnings, ())
        for key in ("normalize_ms", "detect_ms", "queue_wait_ms", "model_load_ms", "inference_ms", "total_ms"):
            self.assertIn(key, result.timings_ms)
        self.assertEqual(result.translation.count("తెలుగు పాఠం"), 2)

    def test_auto_detection_resolves_telugu(self):
        result = run(self.h.service.translate(TranslationRequest(SAMPLES["te"], target="en")))
        self.assertEqual(result.source_language, "te")
        self.assertEqual(result.source_detection.status, "resolved")
        self.assertEqual(self.h.factory.created[0].calls[0][1], "tel_Telu")
        self.assertEqual(self.h.factory.created[0].calls[0][2], "eng_Latn")

    def test_ambiguous_script_asks_for_manual_choice_instead_of_guessing(self):
        with self.assertRaises(LanguageAmbiguousError) as ctx:
            run(self.h.service.translate(TranslationRequest(SAMPLES["hi"], target="en")))
        extra = ctx.exception.extra
        self.assertEqual(set(extra["candidates"]), {"hi", "mr"})
        self.assertEqual(extra["script"], "Devanagari")
        self.assertEqual(self.h.factory.created, [])  # no model was even loaded

    def test_text_in_unlisted_script_is_reported_as_unsupported(self):
        with self.assertRaises(UnsupportedLanguageError):
            run(self.h.service.translate(TranslationRequest("ଓଡ଼ିଆ ଭାଷା ଏକ ସୁନ୍ଦର ଭାଷା", target="en")))

    def test_input_validation(self):
        svc = self.h.service
        with self.assertRaises(InvalidInputError) as ctx:
            run(svc.translate(TranslationRequest(" \u200b\n ", target="te", source="en")))
        self.assertEqual(ctx.exception.code, "empty_text")
        with self.assertRaises(UnsupportedLanguageError):
            run(svc.translate(TranslationRequest("hello there", target="xx", source="en")))
        with self.assertRaises(UnsupportedLanguageError):
            run(svc.translate(TranslationRequest("hello there", target="te", source="xx")))
        with self.assertRaises(SameLanguageError):
            run(svc.translate(TranslationRequest("hello there", target="en", source="en")))

    def test_length_and_segment_limits(self):
        small = Harness(config=TranslationConfig(max_chars=30, max_segments=2))
        try:
            with self.assertRaises(InvalidInputError) as ctx:
                run(small.service.translate(TranslationRequest("x" * 31, target="te", source="en")))
            self.assertEqual(ctx.exception.code, "text_too_long")
            with self.assertRaises(InvalidInputError) as ctx:
                run(small.service.translate(TranslationRequest("One. Two. Three.", target="te", source="en")))
            self.assertEqual(ctx.exception.code, "too_many_segments")
        finally:
            small.close()

    def test_paragraph_structure_is_preserved(self):
        result = run(self.h.service.translate(TranslationRequest("One.\n\nTwo. Three.", target="hi", source="en")))
        parts = result.translation.split("\n\n")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[1].count("हिंदी पाठ"), 2)

    def test_long_sentences_are_split_and_the_split_is_disclosed(self):
        registry = Registry.from_dir()
        nllb = registry.model("nllb-200-distilled-600m")
        registry._models[nllb.id] = replace(nllb, segment_token_limit=5)
        h = Harness(registry=registry)
        try:
            text = "this is a fairly long sentence, with a few clauses; and then some more words follow here"
            result = run(h.service.translate(TranslationRequest(text, target="te", source="en")))
            leg = result.legs[0]
            self.assertGreater(leg.units, result.segments)
            self.assertTrue(leg.split_units)
            self.assertEqual(result.segments, 1)
            self.assertGreater(result.translation.count("తెలుగు పాఠం"), 1)
        finally:
            h.close()

    def test_explicit_model_is_honoured(self):
        result = run(self.h.service.translate(TranslationRequest("Hello world.", target="te", source="en", model_id="mbart50-many-to-many")))
        self.assertEqual(result.legs[0].model_id, "mbart50-many-to-many")
        self.assertEqual(self.h.factory.created[0].calls[0][2], "te_IN")

    def test_unsupported_pair_for_the_only_enabled_model(self):
        h = Harness(policy=RoutingPolicy(enabled_models=frozenset({"mbart50-many-to-many"})))
        try:
            with self.assertRaises(UnsupportedPairError):
                run(h.service.translate(TranslationRequest("ನಮಸ್ಕಾರ ಸ್ನೇಹಿತರೇ ಹೇಗಿದ್ದೀರಿ", target="en", source="kn")))
        finally:
            h.close()


class PivotTests(unittest.TestCase):
    def _registry(self):
        registry = Registry.from_dir()
        nllb = registry.model("nllb-200-distilled-600m")
        registry._models[nllb.id] = replace(nllb, sources=frozenset({"en"}), targets=frozenset({"hi"}))
        mbart = registry.model("mbart50-many-to-many")
        registry._models[mbart.id] = replace(mbart, sources=frozenset({"te"}), targets=frozenset({"en"}))
        return registry

    def test_pivot_runs_two_legs_feeds_the_first_output_to_the_second_and_discloses_it(self):
        h = Harness(registry=self._registry())
        try:
            request = TranslationRequest("ఇది ఒక పరీక్ష. ఇది రెండవది.", target="hi", source="te", allow_pivot=True)
            result = run(h.service.translate(request))
            self.assertEqual(result.pivot_via, "en")
            self.assertEqual([(leg.source, leg.target, leg.model_id) for leg in result.legs],
                 [("te", "en", "mbart50-many-to-many"), ("en", "hi", "nllb-200-distilled-600m")])
            first_outputs = [out for out in (f"translated text {len(s)}" for s in ["ఇది ఒక పరీక్ష.", "ఇది రెండవది."])]
            second_inputs = h.factory.backend_for("nllb-200-distilled-600m").calls[0][0]
            self.assertEqual(second_inputs, first_outputs)
        finally:
            h.close()

    def test_without_consent_there_is_no_pivot(self):
        h = Harness(registry=self._registry())
        try:
            with self.assertRaises(UnsupportedPairError) as ctx:
                run(h.service.translate(TranslationRequest("ఇది ఒక పరీక్ష.", target="hi", source="te")))
            self.assertEqual(ctx.exception.extra["pivot_available_via"], "en")
            self.assertEqual(h.factory.created, [])
        finally:
            h.close()


class OutputValidationTests(unittest.TestCase):
    def _run_with(self, **backend_kwargs):
        h = Harness(factory=FakeFactory(**backend_kwargs))
        try:
            return run(h.service.translate(TranslationRequest("Hello there friend. Second sentence here.", target="te", source="en")))
        finally:
            h.close()

    def test_empty_output_is_an_error_not_a_success(self):
        with self.assertRaises(OutputValidationError) as ctx:
            self._run_with(transform=lambda t, s, g: "   ")
        self.assertEqual(ctx.exception.code, "empty_output")

    def test_wrong_script_is_a_warning_not_a_silent_pass(self):
        result = self._run_with(transform=lambda t, s, g: "this is still english text")
        self.assertIn("target_script_mismatch", [w.code for w in result.warnings])

    def test_unchanged_sentences_are_flagged(self):
        result = self._run_with(transform=lambda t, s, g: t)
        codes = [w.code for w in result.warnings]
        self.assertIn("source_copied", codes)

    def test_length_outliers_are_flagged(self):
        result = self._run_with(transform=lambda t, s, g: "తెలుగు " * 200)
        self.assertIn("length_ratio_outlier", [w.code for w in result.warnings])

    def test_model_returning_wrong_batch_size_is_an_error(self):
        with self.assertRaises(InferenceError) as ctx:
            self._run_with(wrong_count=True)
        self.assertEqual(ctx.exception.code, "batch_size_mismatch")

    def test_backend_exception_is_wrapped_without_leaking_its_message(self):
        with self.assertRaises(InferenceError) as ctx:
            self._run_with(fail_with=RuntimeError("CUDA out of memory while translating: my private sentence"))
        err = ctx.exception
        self.assertEqual(err.code, "out_of_memory")
        self.assertNotIn("private", err.detail + str(err.extra))

    def test_load_failure_surfaces_as_model_load_error(self):
        with self.assertRaises(ModelLoadError):
            self._run_with(fail_load=True)


class ConcurrencyTests(unittest.TestCase):
    def test_full_queue_rejects_new_work_while_earlier_requests_still_finish(self):
        gate = threading.Event()
        h = Harness(factory=FakeFactory(gate=gate), queue_size=1)
        request = TranslationRequest("Hello there friend.", target="te", source="en")

        async def scenario():
            first = asyncio.create_task(h.service.translate(request))
            await asyncio.sleep(0.1)  # worker picks the first job up and blocks on the gate
            second = asyncio.create_task(h.service.translate(request))
            await asyncio.sleep(0.05)  # second job waits in the queue (capacity 1)
            with self.assertRaises(QueueFullError):
                await h.service.translate(request)
            gate.set()
            return await asyncio.gather(first, second)

        try:
            results = run(scenario())
            self.assertEqual(len(results), 2)
            self.assertEqual(h.executor.stats().rejected, 1)
        finally:
            gate.set()
            h.close()

    def test_timeout_is_reported_and_the_service_keeps_working(self):
        gate = threading.Event()
        factory = FakeFactory(gate=gate)
        h = Harness(factory=factory, config=TranslationConfig(job_timeout_s=0.1))
        request = TranslationRequest("Hello there friend.", target="te", source="en")

        async def scenario():
            with self.assertRaises(InferenceTimeoutError):
                await h.service.translate(request)
            gate.set()
            await asyncio.sleep(0.2)
            return await h.service.translate(request)

        try:
            self.assertEqual(run(scenario()).segments, 1)
        finally:
            gate.set()
            h.close()

    def test_cancelling_a_request_stops_work_between_batches(self):
        factory = FakeFactory(delay=0.05)
        h = Harness(factory=factory, config=TranslationConfig(max_batch_size=1, max_segments=50))
        text = " ".join(f"Sentence number {i} is here." for i in range(12))

        async def scenario():
            task = asyncio.create_task(h.service.translate(TranslationRequest(text, target="te", source="en")))
            await asyncio.sleep(0.2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0.3)

        try:
            run(scenario())
            self.assertLess(len(factory.created[0].calls), 12)
        finally:
            h.close()


class ExplainRouteTests(unittest.TestCase):
    def test_explain_route_does_not_load_anything(self):
        h = Harness()
        try:
            plan = h.service.explain_route("te", "en")
            self.assertEqual(plan.legs[0].spec.id, "nllb-200-distilled-600m")
            self.assertEqual(h.factory.created, [])
        finally:
            h.close()


if __name__ == "__main__":
    unittest.main()

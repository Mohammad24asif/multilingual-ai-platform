import unittest
from dataclasses import replace

from app.core.errors import ModelLoadError, RemoteCodeNotAllowedError
from app.domain.registry import Registry
from app.inference.hub import AvailabilityCache
from app.translation.backends.base import BackendContext, GenerationParams
from app.translation.backends.transformers_backends import (
    IndicTrans2Backend,
    MBart50Backend,
    NllbBackend,
    make_backend_factory,
)

SHA = "e" * 40


class FactoryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry.from_dir()
        self.ctx = BackendContext(device="cpu")

    def test_each_family_maps_to_its_backend_without_importing_torch(self):
        factory = make_backend_factory(self.ctx)
        self.assertIsInstance(factory(self.registry.model("nllb-200-distilled-600m")), NllbBackend)
        self.assertIsInstance(factory(self.registry.model("mbart50-many-to-many")), MBart50Backend)

    def test_remote_code_model_is_refused_without_pin_and_allowlist(self):
        spec = self.registry.model("indictrans2-indic-en-dist-200m")
        with self.assertRaises(RemoteCodeNotAllowedError):
            make_backend_factory(self.ctx)(spec)
        pinned = replace(spec, revision=SHA)
        with self.assertRaises(RemoteCodeNotAllowedError):
            make_backend_factory(self.ctx)(pinned)  # pinned but never reviewed
        with self.assertRaises(RemoteCodeNotAllowedError):
            make_backend_factory(self.ctx, frozenset({f"{spec.hf_repo}@{'f' * 40}"}))(pinned)  # wrong commit allowlisted
        backend = make_backend_factory(self.ctx, frozenset({f"{spec.hf_repo}@{SHA}"}))(pinned)
        self.assertIsInstance(backend, IndicTrans2Backend)
        self.assertTrue(backend.remote_code)

    def test_unknown_family_is_an_error(self):
        spec = replace(self.registry.model("nllb-200-distilled-600m"), family="mystery")
        with self.assertRaises(ModelLoadError) as ctx:
            make_backend_factory(self.ctx)(spec)
        self.assertEqual(ctx.exception.code, "unknown_family")

    def test_hub_kwargs_never_allow_downloads_by_default_and_pin_revisions(self):
        spec = replace(self.registry.model("nllb-200-distilled-600m"), revision=SHA)
        backend = NllbBackend(spec, BackendContext(device="cpu"))
        kwargs = backend._common_kwargs()
        self.assertTrue(kwargs["local_files_only"])
        self.assertEqual(kwargs["revision"], SHA)
        self.assertNotIn("trust_remote_code", kwargs)
        it2 = IndicTrans2Backend(self.registry.model("indictrans2-indic-en-dist-200m"), BackendContext(device="cpu", allow_download=True))
        self.assertTrue(it2._common_kwargs()["trust_remote_code"])
        self.assertFalse(it2._common_kwargs()["local_files_only"])


class GenerationParamsTests(unittest.TestCase):
    def test_defaults_and_validation(self):
        self.assertEqual(GenerationParams().num_beams, 4)
        for bad in ({"num_beams": 0}, {"num_beams": 9}, {"max_new_tokens": 4}, {"max_new_tokens": 5000}):
            with self.assertRaises(ValueError):
                GenerationParams(**bad)


class AvailabilityCacheTests(unittest.TestCase):
    def test_results_are_cached_until_the_ttl_expires(self):
        spec = Registry.from_dir().model("nllb-200-distilled-600m")
        now = [0.0]
        calls = []
        cache = AvailabilityCache(lambda s: calls.append(s.id) or True, ttl_s=30, clock=lambda: now[0])
        self.assertTrue(cache(spec))
        self.assertTrue(cache(spec))
        self.assertEqual(len(calls), 1)
        now[0] = 31.0
        cache(spec)
        self.assertEqual(len(calls), 2)
        cache.invalidate()
        cache(spec)
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()

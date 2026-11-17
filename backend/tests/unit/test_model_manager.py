import unittest

from app.core.errors import ModelLoadError, ModelNotDownloadedError
from app.domain.registry import Registry
from app.inference.manager import ModelManager
from tests.fakes import FakeFactory


class ModelManagerTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry.from_dir()
        self.nllb = self.registry.model("nllb-200-distilled-600m")
        self.mbart = self.registry.model("mbart50-many-to-many")

    def test_models_are_loaded_once_and_cached(self):
        factory = FakeFactory()
        manager = ModelManager(factory, max_loaded=2)
        first, load_s = manager.acquire(self.nllb)
        again, load_again = manager.acquire(self.nllb)
        self.assertIs(first, again)
        self.assertEqual(len(factory.created), 1)
        self.assertGreaterEqual(load_s, 0.0)
        self.assertEqual(load_again, 0.0)
        self.assertEqual(manager.statuses()[self.nllb.id].state, "loaded")

    def test_lru_eviction_when_only_one_model_may_be_loaded(self):
        factory = FakeFactory()
        manager = ModelManager(factory, max_loaded=1)
        a, _ = manager.acquire(self.nllb)
        b, _ = manager.acquire(self.mbart)
        self.assertFalse(a.loaded)
        self.assertTrue(b.loaded)
        self.assertEqual(manager.loaded_ids(), [self.mbart.id])
        self.assertEqual(manager.statuses()[self.nllb.id].state, "not_loaded")

    def test_recently_used_model_survives_eviction(self):
        factory = FakeFactory()
        manager = ModelManager(factory, max_loaded=2)
        small = self.registry.model("indictrans2-en-indic-dist-200m")
        manager.acquire(self.nllb)
        manager.acquire(self.mbart)
        manager.acquire(self.nllb)  # nllb is now most recently used
        manager.acquire(small)  # needs room: mbart (least recent) goes
        self.assertEqual(set(manager.loaded_ids()), {self.nllb.id, small.id})

    def test_ram_budget_triggers_eviction(self):
        manager = ModelManager(FakeFactory(), max_loaded=5, ram_budget_mb=4000)
        manager.acquire(self.nllb)  # ~3000 MB
        manager.acquire(self.mbart)  # ~3055 MB: both would not fit in 4000
        self.assertEqual(manager.loaded_ids(), [self.mbart.id])

    def test_model_larger_than_budget_is_refused_without_evicting_others(self):
        manager = ModelManager(FakeFactory(), max_loaded=5, ram_budget_mb=3500)
        manager.acquire(self.nllb)
        big = self.registry.model("indictrans2-en-indic-1b")  # ~5000 MB
        with self.assertRaises(ModelLoadError) as ctx:
            manager.acquire(big)
        self.assertEqual(ctx.exception.code, "exceeds_ram_budget")
        self.assertEqual(manager.loaded_ids(), [self.nllb.id])

    def test_not_downloaded_raises_actionable_error_before_loading(self):
        factory = FakeFactory()
        manager = ModelManager(factory, is_downloaded=lambda spec: False)
        with self.assertRaises(ModelNotDownloadedError) as ctx:
            manager.acquire(self.nllb)
        self.assertIn("download_models.py", ctx.exception.extra["hint"])
        self.assertEqual(factory.created, [])

    def test_load_failure_is_reported_without_the_library_message(self):
        factory = FakeFactory(fail_load=True)
        manager = ModelManager(factory)
        with self.assertRaises(ModelLoadError) as ctx:
            manager.acquire(self.nllb)
        text = ctx.exception.detail + str(ctx.exception.extra)
        self.assertNotIn("secret", text)
        self.assertNotIn("user text", text)
        self.assertEqual(ctx.exception.extra["error_type"], "RuntimeError")
        status = manager.statuses()[self.nllb.id]
        self.assertEqual((status.state, status.last_error_code), ("failed", "load_error"))
        self.assertEqual(manager.loaded_ids(), [])

    def test_unload_all_releases_everything(self):
        factory = FakeFactory()
        manager = ModelManager(factory, max_loaded=3)
        backend, _ = manager.acquire(self.nllb)
        manager.unload_all()
        self.assertFalse(backend.loaded)
        self.assertEqual(manager.loaded_ids(), [])

    def test_invalid_max_loaded(self):
        with self.assertRaises(ValueError):
            ModelManager(FakeFactory(), max_loaded=0)


if __name__ == "__main__":
    unittest.main()

import unittest
from dataclasses import replace

from app.core.errors import (
    ModelNotDownloadedError,
    SameLanguageError,
    UnknownModelError,
    UnsupportedLanguageError,
    UnsupportedPairError,
)
from app.domain.registry import Registry
from app.translation.router import RoutingPolicy, TranslationRouter

SHA = "c" * 40


def make_router(registry=None, **policy):
    return TranslationRouter(registry or Registry.from_dir(), RoutingPolicy(**policy))


class DefaultRoutingTests(unittest.TestCase):
    def test_prefers_nllb_over_mbart_when_both_qualify(self):
        route = make_router().route("te", "en")
        self.assertEqual(route.spec.id, "nllb-200-distilled-600m")
        self.assertEqual({c.spec.id for c in route.considered if c.accepted}, {"nllb-200-distilled-600m", "mbart50-many-to-many"})

    def test_kannada_skips_mbart_with_reason(self):
        route = make_router().route("kn", "en")
        self.assertEqual(route.spec.id, "nllb-200-distilled-600m")
        mbart = next(c for c in route.considered if c.spec.id == "mbart50-many-to-many")
        self.assertIn("source_language_not_supported", mbart.reasons)

    def test_indictrans2_is_rejected_until_reviewed_and_enabled(self):
        route = make_router().route("te", "en")
        it2 = next(c for c in route.considered if c.spec.id == "indictrans2-indic-en-dist-200m")
        self.assertIn("disabled", it2.reasons)
        self.assertIn("remote_code_not_reviewed", it2.reasons)

    def test_unknown_language_and_same_language(self):
        with self.assertRaises(UnsupportedLanguageError):
            make_router().route("xx", "en")
        with self.assertRaises(SameLanguageError):
            make_router().route("te", "te")

    def test_explicit_model_choice_is_respected_or_rejected_never_substituted(self):
        router = make_router()
        self.assertEqual(router.route("te", "hi", model_id="mbart50-many-to-many").spec.id, "mbart50-many-to-many")
        with self.assertRaises(UnsupportedPairError) as ctx:
            router.route("kn", "en", model_id="mbart50-many-to-many")
        self.assertIn("source_language_not_supported", ctx.exception.extra["reasons"]["mbart50-many-to-many"])
        with self.assertRaises(UnknownModelError):
            router.route("te", "en", model_id="does-not-exist")


class LicenceModeTests(unittest.TestCase):
    def test_commercial_mode_excludes_research_only_and_unverified_models(self):
        router = make_router(licence_mode="commercial")
        with self.assertRaises(UnsupportedPairError) as ctx:
            router.route("te", "en")
        reasons = ctx.exception.extra["reasons"]
        self.assertIn("licence_not_allowed:non_commercial", reasons["nllb-200-distilled-600m"])
        self.assertIn("licence_unverified", reasons["mbart50-many-to-many"])

    def test_commercial_mode_accepts_a_verified_permissive_model(self):
        registry = Registry.from_dir()
        mbart = registry.model("mbart50-many-to-many")
        verified = replace(mbart, licence=replace(mbart.licence, verified=True))
        registry._models[mbart.id] = verified  # test-only substitution
        route = make_router(registry, licence_mode="commercial").route("te", "en")
        self.assertEqual(route.spec.id, "mbart50-many-to-many")

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            RoutingPolicy(licence_mode="anything")


class RemoteCodeAndResourceTests(unittest.TestCase):
    def _registry_with_pinned_it2(self):
        registry = Registry.from_dir()
        spec = registry.model("indictrans2-indic-en-dist-200m")
        registry._models[spec.id] = replace(spec, revision=SHA)
        return registry, spec

    def test_remote_code_model_needs_pin_and_allowlist_and_enablement(self):
        registry, spec = self._registry_with_pinned_it2()
        allow = frozenset({f"{spec.hf_repo}@{SHA}"})
        enabled = frozenset({spec.id})
        self.assertEqual(
            make_router(registry, enabled_models=enabled, remote_code_allowlist=allow).route("te", "en").spec.id, spec.id
        )
        with self.assertRaises(UnsupportedPairError):  # allowlisted but not enabled
            make_router(registry, enabled_models=frozenset(), remote_code_allowlist=allow).route("te", "en")
        wrong = frozenset({f"{spec.hf_repo}@{'d' * 40}"})
        with self.assertRaises(UnsupportedPairError):  # enabled but allowlist names another commit
            make_router(registry, enabled_models=enabled, remote_code_allowlist=wrong).route("te", "en")

    def test_ram_budget_excludes_large_models(self):
        router = make_router(ram_budget_mb=2000)
        with self.assertRaises(UnsupportedPairError) as ctx:
            router.route("te", "en")
        self.assertIn("exceeds_ram_budget", ctx.exception.extra["reasons"]["nllb-200-distilled-600m"])

    def test_enabled_models_override_defaults(self):
        route = make_router(enabled_models=frozenset({"mbart50-many-to-many"})).route("te", "en")
        self.assertEqual(route.spec.id, "mbart50-many-to-many")


class AvailabilityTests(unittest.TestCase):
    def test_unavailable_best_model_falls_back_to_available_one(self):
        router = TranslationRouter(Registry.from_dir(), RoutingPolicy(), is_available=lambda s: s.id == "mbart50-many-to-many")
        self.assertEqual(router.route("te", "en").spec.id, "mbart50-many-to-many")

    def test_nothing_downloaded_raises_actionable_error(self):
        router = TranslationRouter(Registry.from_dir(), RoutingPolicy(), is_available=lambda s: False)
        with self.assertRaises(ModelNotDownloadedError) as ctx:
            router.route("te", "en")
        self.assertIn("nllb-200-distilled-600m", ctx.exception.extra["model_ids"])
        self.assertIn("download_models.py", ctx.exception.extra["hint"])


class PivotTests(unittest.TestCase):
    def _split_registry(self):
        registry = Registry.from_dir()
        # Two one-way models: te->en (mBART slot) and en->hi (NLLB slot). Neither can do te->hi directly.
        nllb = registry.model("nllb-200-distilled-600m")
        registry._models[nllb.id] = replace(nllb, sources=frozenset({"en"}), targets=frozenset({"hi"}))
        mbart = registry.model("mbart50-many-to-many")
        registry._models[mbart.id] = replace(mbart, sources=frozenset({"te"}), targets=frozenset({"en"}))
        return registry

    def test_no_silent_pivot(self):
        router = make_router(self._split_registry())
        with self.assertRaises(UnsupportedPairError) as ctx:
            router.plan("te", "hi")
        self.assertEqual(ctx.exception.extra["pivot_available_via"], "en")
        self.assertIn("allow_pivot=true", ctx.exception.detail)

    def test_pivot_is_planned_and_disclosed_when_allowed(self):
        plan = make_router(self._split_registry()).plan("te", "hi", allow_pivot=True)
        self.assertTrue(plan.is_pivot)
        self.assertEqual(plan.pivot_via, "en")
        self.assertEqual([(leg.source, leg.target) for leg in plan.legs], [("te", "en"), ("en", "hi")])
    def test_direct_route_never_pivots(self):
        plan = make_router().plan("te", "hi", allow_pivot=True)
        self.assertFalse(plan.is_pivot)
        self.assertEqual(len(plan.legs), 1)

    def test_pivot_not_attempted_with_explicit_model(self):
        with self.assertRaises(UnsupportedPairError):
            make_router(self._split_registry()).plan("te", "hi", model_id="mbart50-many-to-many", allow_pivot=True)

    def test_no_pivot_available_raises_original_error(self):
        router = make_router(enabled_models=frozenset({"mbart50-many-to-many"}))
        with self.assertRaises(UnsupportedPairError):
            router.plan("kn", "pa", allow_pivot=True)


class SupportedLanguagesTests(unittest.TestCase):
    def test_default_policy_support_matrix(self):
        support = make_router().supported_languages()
        self.assertTrue(all(v["source"] and v["target"] for v in support.values()))  # NLLB covers all eleven

    def test_commercial_mode_without_verified_models_supports_nothing(self):
        support = make_router(licence_mode="commercial").supported_languages()
        self.assertFalse(any(v["source"] or v["target"] for v in support.values()))

    def test_mbart_only_policy_drops_kannada_and_punjabi(self):
        support = make_router(enabled_models=frozenset({"mbart50-many-to-many"})).supported_languages()
        self.assertFalse(support["kn"]["source"])
        self.assertFalse(support["pa"]["target"])
        self.assertTrue(support["te"]["source"])


if __name__ == "__main__":
    unittest.main()

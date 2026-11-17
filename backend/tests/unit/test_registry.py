import unittest

from app.domain.registry import Registry, RegistryError

TARGET_LANGS = {"en", "te", "hi", "ta", "kn", "ml", "bn", "mr", "gu", "ur", "pa"}


class ShippedRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry.from_dir()

    def test_target_language_list_is_registered(self):
        self.assertEqual({l.code for l in self.registry.languages()}, TARGET_LANGS)

    def test_every_language_has_a_script_and_native_name(self):
        for lang in self.registry.languages():
            self.assertTrue(lang.scripts, lang.code)
            self.assertTrue(lang.native_name, lang.code)
        self.assertTrue(self.registry.language("ur").rtl)

    def test_mbart50_excludes_kannada_and_punjabi_per_model_card(self):
        mbart = self.registry.model("mbart50-many-to-many")
        self.assertNotIn("kn", mbart.sources)
        self.assertNotIn("pa", mbart.sources)
        for code in ("en", "te", "hi", "ta", "ml", "bn", "mr", "gu", "ur"):
            self.assertIn(code, mbart.sources)
            self.assertIn(code, mbart.targets)
        self.assertEqual(mbart.model_code("te"), "te_IN")
        self.assertEqual(mbart.model_code("en"), "en_XX")

    def test_nllb_covers_all_eleven_languages_with_flores_codes(self):
        nllb = self.registry.model("nllb-200-distilled-600m")
        self.assertEqual(nllb.sources, frozenset(TARGET_LANGS))
        self.assertEqual(nllb.model_code("te"), "tel_Telu")
        self.assertEqual(nllb.model_code("ur"), "urd_Arab")
        self.assertEqual(nllb.licence.klass.value, "non_commercial")

    def test_indictrans2_direction_rules(self):
        en_indic = self.registry.model("indictrans2-en-indic-1b")
        indic_en = self.registry.model("indictrans2-indic-en-1b")
        indic_indic = self.registry.model("indictrans2-indic-indic-1b")
        self.assertTrue(en_indic.supports("en", "te"))
        self.assertFalse(en_indic.supports("te", "en"))
        self.assertTrue(indic_en.supports("te", "en"))
        self.assertFalse(indic_en.supports("en", "te"))
        self.assertTrue(indic_indic.supports("te", "ta"))
        self.assertFalse(indic_indic.supports("en", "te"))

    def test_remote_code_models_are_disabled_by_default_and_unpinned(self):
        for spec in self.registry.models():
            if spec.requires_remote_code:
                self.assertFalse(spec.enabled_by_default, spec.id)
                self.assertFalse(spec.revision_pinned, spec.id)

    def test_same_language_is_never_supported(self):
        for spec in self.registry.models():
            self.assertFalse(spec.supports("te", "te"))

    def test_estimated_ram_is_derived_from_parameter_count(self):
        self.assertEqual(self.registry.model("nllb-200-distilled-600m").estimated_ram_mb, 3000)

    def test_script_candidates_include_unlisted_languages(self):
        devanagari = {code for code, _name, _listed in self.registry.languages_for_script("Devanagari")}
        self.assertTrue({"hi", "mr", "ne", "sa"} <= devanagari)
        self.assertTrue(self.registry.script_is_open("Latin"))
        self.assertFalse(self.registry.script_is_open("Telugu"))

    def test_every_model_has_evidence_and_licence_metadata(self):
        for spec in self.registry.models():
            self.assertIn("checked", spec.evidence, spec.id)
            self.assertTrue(spec.evidence.get("urls"), spec.id)
            self.assertTrue(spec.licence.spdx, spec.id)


class RegistryValidationTests(unittest.TestCase):
    def _docs(self):
        langs = {"languages": [{"code": "en", "name": "English", "scripts": ["Latin"]}, {"code": "te", "name": "Telugu", "scripts": ["Telugu"]}]}
        models = {
            "code_sets": {"x": {"en": "e", "te": "t"}},
            "models": [{"id": "m", "family": "nllb", "hf_repo": "a/b", "licence": {"spdx": "MIT", "class": "permissive"}, "code_set": "x"}],
        }
        return langs, models

    def test_valid_minimal_documents_load(self):
        langs, models = self._docs()
        registry = Registry.from_documents(langs, models)
        self.assertEqual(registry.model("m").sources, frozenset({"en", "te"}))

    def test_problems_are_all_reported(self):
        langs, models = self._docs()
        models["models"].append({"id": "m", "family": "nllb", "hf_repo": "a/c", "licence": {"spdx": "MIT", "class": "weird"}, "code_set": "nope"})
        models["code_sets"]["x"]["zz"] = "z"
        with self.assertRaises(RegistryError) as ctx:
            Registry.from_documents(langs, models)
        message = str(ctx.exception)
        self.assertIn("duplicate model id m", message)
        self.assertIn("unknown code_set", message)
        self.assertIn("missing from languages.json", message)

    def test_lock_file_pins_revision_and_verifies_licence(self):
        langs, models = self._docs()
        sha = "a" * 40
        lock = {"models": {"m": {"revision": sha, "hub_licence": "MIT"}}}
        spec = Registry.from_documents(langs, models, lock).model("m")
        self.assertEqual(spec.revision, sha)
        self.assertTrue(spec.revision_pinned)
        self.assertTrue(spec.licence.verified)

    def test_licence_mismatch_in_lock_downgrades_to_unknown(self):
        langs, models = self._docs()
        lock = {"models": {"m": {"revision": "b" * 40, "hub_licence": "cc-by-nc-4.0"}}}
        spec = Registry.from_documents(langs, models, lock).model("m")
        self.assertEqual(spec.licence.klass.value, "unknown")
        self.assertFalse(spec.licence.verified)


if __name__ == "__main__":
    unittest.main()

import unittest

from app.detection.detector import LanguageDetector
from app.domain.registry import Registry
from tests.test_samples import SAMPLES


class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = LanguageDetector(Registry.from_dir())

    def test_unique_script_languages_resolve_without_a_confidence_number(self):
        for code in ("te", "ta", "kn", "ml", "gu", "pa"):
            with self.subTest(language=code):
                result = self.detector.detect(SAMPLES[code])
                self.assertEqual(result.status, "resolved")
                self.assertEqual(result.language, code)
                self.assertEqual(result.method, "unique_script")
                self.assertFalse(hasattr(result, "confidence"))

    def test_kannada_note_mentions_tulu(self):
        result = self.detector.detect(SAMPLES["kn"])
        self.assertTrue(any("Tulu" in n for n in result.notes))

    def test_bengali_script_is_ambiguous_because_assamese_shares_it(self):
        result = self.detector.detect(SAMPLES["bn"])
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(result.candidates, ("bn",))
        self.assertIn("Assamese", result.unlisted_candidates)

    def test_devanagari_asks_hindi_or_marathi(self):
        for code in ("hi", "mr"):
            result = self.detector.detect(SAMPLES[code])
            self.assertEqual(result.status, "ambiguous")
            self.assertEqual(set(result.candidates), {"hi", "mr"})
            self.assertIn("Nepali", result.unlisted_candidates)
            self.assertIsNone(result.language)

    def test_odia_script_is_reported_as_unsupported_not_misdetected(self):
        result = self.detector.detect("ଓଡ଼ିଆ ଭାଷା ଏକ ସୁନ୍ଦର ଭାଷା")
        self.assertEqual(result.status, "unsupported_language")
        self.assertEqual(result.language, "or")

    def test_arabic_script_with_urdu_letters_suggests_but_does_not_decide(self):
        result = self.detector.detect(SAMPLES["ur"])
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(result.suggested, "ur")
        self.assertIsNone(result.language)

    def test_english_prose_resolves_on_function_word_evidence(self):
        result = self.detector.detect("The weather is pleasant today, and we are going to the market with them.")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.language, "en")
        self.assertEqual(result.method, "english_function_words")

    def test_short_or_romanised_latin_text_is_not_called_english(self):
        for text in ("Hello", "How are you", "main kal bazaar jaa raha hoon aur woh ghar par tha", "nenu repu market ki veltunnanu"):
            with self.subTest(text=text):
                result = self.detector.detect(text)
                self.assertEqual(result.status, "ambiguous")
                self.assertEqual(result.suggested, "en")

    def test_digits_and_punctuation_are_insufficient(self):
        result = self.detector.detect("12 ?! 34")
        self.assertEqual(result.status, "insufficient_text")

    def test_code_mixed_text_dominated_by_telugu_resolves(self):
        result = self.detector.detect("రేపు ఉదయం meeting ఉంది కాబట్టి ఆఫీసుకు త్వరగా రావాలి")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.language, "te")

    def test_evenly_mixed_scripts_are_ambiguous(self):
        result = self.detector.detect("hello world తెలుగు పాఠం")
        self.assertEqual(result.status, "ambiguous")
        self.assertIn("mixed_scripts", result.notes)
        self.assertTrue({"en", "te"} <= set(result.candidates))

    def test_script_share_is_observed_fraction(self):
        result = self.detector.detect(SAMPLES["te"])
        self.assertGreater(result.script_share, 0.99)
        self.assertEqual(result.script, "Telugu")


if __name__ == "__main__":
    unittest.main()

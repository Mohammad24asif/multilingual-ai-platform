import unittest

from app.text.scripts import profile_text, script_of

SAMPLES = {
    "Telugu": "నమస్కారం, మీరు ఎలా ఉన్నారు?",
    "Devanagari": "नमस्ते, आप कैसे हैं?",
    "Tamil": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?",
    "Kannada": "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?",
    "Malayalam": "നമസ്കാരം, സുഖമാണോ?",
    "Bengali": "নমস্কার, আপনি কেমন আছেন?",
    "Gujarati": "નમસ્તે, તમે કેમ છો?",
    "Gurmukhi": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?",
    "Arabic": "السلام علیکم، آپ کیسے ہیں؟",
    "Latin": "Hello, how are you?",
}


class ScriptTests(unittest.TestCase):
    def test_dominant_script_for_each_sample(self):
        for expected, text in SAMPLES.items():
            with self.subTest(script=expected):
                profile = profile_text(text)
                self.assertEqual(profile.dominant, expected)
                self.assertGreater(profile.dominant_share, 0.99)

    def test_digits_and_punctuation_have_no_script(self):
        profile = profile_text("1234 ... !!! ?? --")
        self.assertIsNone(profile.dominant)
        self.assertEqual(profile.total, 0)
        self.assertEqual(profile.ranked, ())

    def test_combining_marks_are_counted_with_their_script(self):
        # Telugu vowel signs and virama are combining marks inside the Telugu block
        self.assertEqual(script_of("\u0c4d"), "Telugu")
        self.assertEqual(script_of("\u0c3e"), "Telugu")

    def test_digits_in_indic_scripts_are_not_letters(self):
        self.assertIsNone(script_of("\u0c67"))  # Telugu digit one
        self.assertIsNone(script_of("\u0966"))  # Devanagari digit zero

    def test_code_mixed_text_reports_both_scripts(self):
        profile = profile_text("Meeting రేపు ఉదయం ten గంటలకు")
        scripts = dict(profile.ranked)
        self.assertIn("Telugu", scripts)
        self.assertIn("Latin", scripts)
        self.assertAlmostEqual(sum(scripts.values()), 1.0)
        self.assertEqual(profile.dominant, "Telugu")

    def test_shares_are_observed_fractions(self):
        profile = profile_text("aaaa" + "ఆఆ")
        self.assertAlmostEqual(profile.share("Latin"), 4 / 6)
        self.assertAlmostEqual(profile.share("Telugu"), 2 / 6)
        self.assertEqual(profile.share("Tamil"), 0.0)

    def test_danda_is_not_a_letter(self):
        self.assertIsNone(script_of("\u0964"))


if __name__ == "__main__":
    unittest.main()

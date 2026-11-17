import random
import unittest

from app.text.normalize import RLM, ZWJ, ZWNJ, normalize_text


class NormalizeTests(unittest.TestCase):
    def test_nfc_composes(self):
        self.assertEqual(normalize_text("e\u0301").text, "\u00e9")

    def test_zwj_and_zwnj_are_preserved(self):
        telugu = "క్" + ZWNJ + "ష"
        malayalam = "ന" + ZWJ + "ു"
        self.assertEqual(normalize_text(telugu).text, telugu)
        self.assertEqual(normalize_text(malayalam).text, malayalam)

    def test_emoji_zwj_sequence_is_preserved(self):
        family = "\U0001F468" + ZWJ + "\U0001F469" + ZWJ + "\U0001F467"
        self.assertEqual(normalize_text(family).text, family)

    def test_rlm_is_preserved_for_urdu(self):
        text = "اردو" + RLM + " text"
        self.assertIn(RLM, normalize_text(text).text)

    def test_invisible_junk_is_removed(self):
        text = "\ufeffHel\u00adlo\u2060 wor\u200bld\x00"
        result = normalize_text(text)
        self.assertEqual(result.text, "Hello world")
        self.assertTrue(result.changed)
        self.assertGreaterEqual(result.stats["format_removed"], 4)
        self.assertEqual(result.stats["control_removed"], 1)

    def test_line_endings_and_special_spaces(self):
        text = "a\r\nb\rc\u2028d\u00a0e\u3000f"
        self.assertEqual(normalize_text(text).text, "a\nb\nc\nd e f")

    def test_whitespace_is_collapsed_but_paragraphs_survive(self):
        text = "  one   two \t three  \n\n\n\n four  \n  five  "
        self.assertEqual(normalize_text(text).text, "one two three\n\nfour\nfive")

    def test_original_is_kept_separately(self):
        result = normalize_text("  hi  ")
        self.assertEqual(result.original, "  hi  ")
        self.assertEqual(result.text, "hi")

    def test_empty_and_whitespace_only(self):
        self.assertEqual(normalize_text("").text, "")
        self.assertEqual(normalize_text(" \n\t ").text, "")

    def test_idempotent_and_never_drops_joiners_under_fuzzing(self):
        rng = random.Random(20261116)
        alphabet = [
            "a", "e", "Z", " ", " ", "\t", "\n", "\r", "\u00a0", "\u200b", ZWNJ, ZWJ, "\ufeff", "\u00ad",
            "\u0301", "\u0c15", "\u0c4d", "\u0c37", "\u0915", "\u094d", "\u0964", "1", ".", "\x07", "\u2028",
        ]
        for _ in range(4000):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
            once = normalize_text(text).text
            twice = normalize_text(once).text
            self.assertEqual(once, twice, repr(text))
            self.assertEqual(
                once.count(ZWJ) + once.count(ZWNJ), text.count(ZWJ) + text.count(ZWNJ), repr(text)
            )
            self.assertNotIn("\r", once)
            self.assertNotIn("\ufeff", once)
            self.assertNotIn("\u00ad", once)


if __name__ == "__main__":
    unittest.main()

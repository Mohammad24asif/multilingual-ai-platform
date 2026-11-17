import random
import unittest

from app.text.segment import segment_text


def texts(source: str) -> list[str]:
    return segment_text(source).texts()


class SegmentTests(unittest.TestCase):
    def test_basic_english(self):
        self.assertEqual(texts("Hello world. How are you? I am fine!"), ["Hello world.", "How are you?", "I am fine!"])

    def test_abbreviations_and_times(self):
        src = "Dr. Rao visited Hyderabad. He arrived at 3.30 p.m. today."
        self.assertEqual(texts(src), ["Dr. Rao visited Hyderabad.", "He arrived at 3.30 p.m. today."])

    def test_decimal_numbers(self):
        self.assertEqual(texts("Pi is 3.14. That is all."), ["Pi is 3.14.", "That is all."])

    def test_hindi_danda(self):
        self.assertEqual(
            texts("यह पहला वाक्य है। यह दूसरा वाक्य है।"), ["यह पहला वाक्य है।", "यह दूसरा वाक्य है।"]
        )

    def test_telugu_full_stop(self):
        self.assertEqual(texts("ఇది మొదటి వాక్యం. ఇది రెండవ వాక్యం."), ["ఇది మొదటి వాక్యం.", "ఇది రెండవ వాక్యం."])

    def test_urdu_full_stop(self):
        self.assertEqual(texts("یہ پہلا جملہ ہے۔ یہ دوسرا جملہ ہے۔"), ["یہ پہلا جملہ ہے۔", "یہ دوسرا جملہ ہے۔"])

    def test_paragraphs_keep_their_separator(self):
        seg = segment_text("Para one.\n\nPara two.")
        self.assertEqual(seg.texts(), ["Para one.", "Para two."])
        self.assertEqual(seg.segments[0].sep, "\n\n")

    def test_lines_without_terminators(self):
        self.assertEqual(texts("Title\nBody text here."), ["Title", "Body text here."])

    def test_list_numbering_is_not_a_sentence(self):
        self.assertEqual(texts("1. Introduction\n2. Methods"), ["1. Introduction", "2. Methods"])

    def test_quotes_stay_with_their_sentence(self):
        self.assertEqual(texts('He said "Stop." Then he left.'), ['He said "Stop."', "Then he left."])

    def test_ellipsis_before_lowercase_does_not_split(self):
        self.assertEqual(texts("Wait... what? Yes."), ["Wait... what?", "Yes."])

    def test_question_mark_always_splits(self):
        self.assertEqual(texts("Really? yes."), ["Really?", "yes."])

    def test_leading_and_trailing_whitespace_survive_render(self):
        seg = segment_text("  Hi there.  ")
        self.assertEqual(seg.lead, "  ")
        self.assertEqual(seg.render(seg.texts()), "  Hi there.  ")

    def test_empty_and_blank(self):
        self.assertEqual(texts(""), [])
        blank = segment_text(" \n ")
        self.assertEqual(blank.segments, ())
        self.assertEqual(blank.render([]), " \n ")

    def test_render_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            segment_text("One. Two.").render(["only one"])

    def test_render_substitutes_translations_with_original_spacing(self):
        seg = segment_text("One.\n\nTwo. Three.")
        self.assertEqual(seg.render(["A", "B", "C"]), "A\n\nB C")

    def test_lossless_and_well_formed_under_fuzzing(self):
        rng = random.Random(42)
        alphabet = list("abcXYZ .?!\n\t,।۔…\"'()31 ") + list("ఇదిహ్") + ["Dr.", " e.g. ", "\u00a0"]
        for _ in range(6000):
            source = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
            seg = segment_text(source)
            self.assertEqual(seg.render(seg.texts()), source, repr(source))
            previous_end = 0
            for s in seg.segments:
                self.assertTrue(s.text, repr(source))
                self.assertEqual(s.text, s.text.strip(), repr(source))
                self.assertEqual(source[s.start : s.end], s.text, repr(source))
                self.assertGreaterEqual(s.start, previous_end)
                previous_end = s.end


if __name__ == "__main__":
    unittest.main()

import random
import unittest

from app.text.chunk import merge_units, plan_batches, plan_units


def words(text: str) -> int:
    return len(text.split())


class PlanUnitsTests(unittest.TestCase):
    def test_short_segments_are_untouched(self):
        units = plan_units(["one two", "three"], count_tokens=words, max_tokens=5)
        self.assertEqual([u.text for u in units], ["one two", "three"])
        self.assertTrue(all(u.split is None for u in units))

    def test_long_segment_is_split_at_clauses_first(self):
        seg = "alpha beta gamma, delta epsilon zeta, eta theta iota"
        units = plan_units([seg], count_tokens=words, max_tokens=4)
        self.assertTrue(all(words(u.text) <= 4 for u in units))
        self.assertTrue(all(u.split == "clause" for u in units))
        self.assertEqual(merge_units(units, [u.text for u in units], 1), [seg])

    def test_falls_back_to_word_splitting(self):
        seg = "one two three four five six seven eight nine ten"
        units = plan_units([seg], count_tokens=words, max_tokens=3)
        self.assertTrue(all(words(u.text) <= 3 for u in units))
        self.assertIn("words", {u.split for u in units})
        self.assertEqual(merge_units(units, [u.text for u in units], 1), [seg])

    def test_character_split_is_last_resort(self):
        units = plan_units(["x" * 50], count_tokens=len, max_tokens=10)
        self.assertEqual(len(units), 5)
        self.assertTrue(all(u.split == "chars" and len(u.text) <= 10 for u in units))
        self.assertEqual("".join(u.text for u in units), "x" * 50)

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            plan_units(["a"], count_tokens=words, max_tokens=0)

    def test_merge_rejects_wrong_length(self):
        units = plan_units(["a b"], count_tokens=words, max_tokens=5)
        with self.assertRaises(ValueError):
            merge_units(units, [], 1)

    def test_identity_round_trip_under_fuzzing(self):
        rng = random.Random(7)
        vocabulary = ["alpha", "beta,", "gamma;", "delta", "eps:", "zeta", "eta", "ఇది", "హ,"]
        for _ in range(1500):
            segments = [
                " ".join(rng.choice(vocabulary) for _ in range(rng.randint(1, 30))).rstrip(",;:")
                for _ in range(rng.randint(1, 4))
            ]
            limit = rng.randint(1, 8)
            units = plan_units(segments, count_tokens=words, max_tokens=limit)
            for u in units:
                self.assertLessEqual(words(u.text), limit)
            merged = merge_units(units, [u.text for u in units], len(segments))
            self.assertEqual(merged, segments)


class PlanBatchesTests(unittest.TestCase):
    def test_every_unit_appears_exactly_once_and_limits_hold(self):
        rng = random.Random(99)
        for _ in range(500):
            segments = [" ".join(["w"] * rng.randint(1, 12)) for _ in range(rng.randint(1, 25))]
            units = plan_units(segments, count_tokens=words, max_tokens=12)
            size, budget = rng.randint(1, 6), rng.randint(4, 40)
            batches = plan_batches(units, count_tokens=words, max_batch_size=size, max_batch_tokens=budget)
            flat = [i for b in batches for i in b]
            self.assertEqual(sorted(flat), list(range(len(units))))
            for b in batches:
                self.assertLessEqual(len(b), size)
                if len(b) > 1:
                    self.assertLessEqual(max(words(units[i].text) for i in b) * len(b), budget)

    def test_similar_lengths_are_grouped(self):
        units = plan_units(["a " * 2, "b " * 20, "c " * 2, "d " * 21], count_tokens=words, max_tokens=50)
        batches = plan_batches(units, count_tokens=words, max_batch_size=2, max_batch_tokens=100)
        lengths = [sorted(words(units[i].text) for i in b) for b in batches]
        self.assertEqual(lengths, [[2, 2], [20, 21]])

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):
            plan_batches([], count_tokens=words, max_batch_size=0, max_batch_tokens=1)


if __name__ == "__main__":
    unittest.main()

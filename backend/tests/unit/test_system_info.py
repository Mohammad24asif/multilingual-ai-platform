import unittest

from app.inference.system_info import choose_device, get_system_info


class SystemInfoTests(unittest.TestCase):
    def test_reports_python_and_memory(self):
        info = get_system_info()
        self.assertRegex(info["python"], r"^3\.\d+")
        self.assertGreater(info["ram_total_mb"], 0)
        self.assertLessEqual(info["ram_available_mb"], info["ram_total_mb"])
        self.assertIn("torch", info)
        self.assertIn("installed", info["torch"])

    def test_device_selection_never_requires_a_gpu(self):
        self.assertEqual(choose_device("auto", cuda_available=False), "cpu")
        self.assertEqual(choose_device("auto", cuda_available=True), "cuda")
        self.assertEqual(choose_device("cpu", cuda_available=True), "cpu")

    def test_explicit_cuda_without_cuda_is_an_error_not_a_silent_fallback(self):
        with self.assertRaises(ValueError):
            choose_device("cuda", cuda_available=False)
        self.assertEqual(choose_device("cuda", cuda_available=True), "cuda")

    def test_invalid_preference(self):
        with self.assertRaises(ValueError):
            choose_device("tpu")


if __name__ == "__main__":
    unittest.main()

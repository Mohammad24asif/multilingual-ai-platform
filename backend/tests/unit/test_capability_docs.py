import unittest
from pathlib import Path

from app.capability_docs import render_capabilities
from app.domain.registry import Registry

DOC = Path(__file__).resolve().parents[3] / "docs" / "CAPABILITIES.md"


class CapabilityDocsTests(unittest.TestCase):
    def test_rendering_is_deterministic(self):
        registry = Registry.from_dir()
        self.assertEqual(render_capabilities(registry), render_capabilities(registry))

    def test_committed_document_matches_the_registry(self):
        if not DOC.exists():
            self.skipTest("docs/CAPABILITIES.md not present")
        self.assertEqual(
            DOC.read_text(encoding="utf-8"),
            render_capabilities(Registry.from_dir()),
            "Registry changed: run `python scripts/generate_capability_docs.py` and commit docs/CAPABILITIES.md",
        )

    def test_document_states_the_mbart_gap_and_the_research_licence(self):
        text = render_capabilities(Registry.from_dir())
        self.assertIn("not Kannada or Punjabi", text)
        self.assertIn("CC-BY-NC-4.0 (non_commercial)", text)
        self.assertIn("codes_verified: false", text)


if __name__ == "__main__":
    unittest.main()

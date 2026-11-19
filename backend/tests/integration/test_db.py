"""Database foundation checks. They need SQLAlchemy, so they are skipped where it is not installed."""

import asyncio
import unittest

try:
    import sqlalchemy  # noqa: F401
except ImportError:
    raise unittest.SkipTest("sqlalchemy is not installed")

from app.db.base import Base
from app.db.repository import HistoryRepository
from app.db.session import create_db_engine, create_session_factory
from app.runtime import Container, RuntimeConfig
from app.translation.types import TranslationRequest
from tests.fakes import FakeFactory


class HistoryRepositoryTests(unittest.TestCase):
    def setUp(self):
        engine = create_db_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.repo = HistoryRepository(create_session_factory(engine))
        container = Container(RuntimeConfig(), backend_factory=FakeFactory(), availability=lambda s: True, device="cpu")
        container.start()
        self.addCleanup(container.stop)
        self.result = asyncio.run(container.translation.translate(TranslationRequest("Hello there friend.", target="te", source="en")))

    def test_metadata_only_by_default(self):
        self.repo.record(self.result, source_text="Hello there friend.")
        row = self.repo.recent()[0]
        self.assertFalse(row.text_stored)
        self.assertIsNone(row.source_text)
        self.assertIsNone(row.output_text)
        self.assertEqual(row.source_language, "en")
        self.assertEqual(row.model_ids, "nllb-200-distilled-600m")

    def test_text_is_stored_only_with_explicit_consent_and_can_be_deleted(self):
        self.repo.record(self.result, store_text=True, source_text="Hello there friend.")
        row = self.repo.recent()[0]
        self.assertTrue(row.text_stored)
        self.assertEqual(row.source_text, "Hello there friend.")
        self.assertEqual(self.repo.count(), 1)
        self.assertEqual(self.repo.delete_all(), 1)
        self.assertEqual(self.repo.count(), 0)


if __name__ == "__main__":
    unittest.main()

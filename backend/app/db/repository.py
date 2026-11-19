"""History persistence. Text is stored ONLY when the caller passes store_text=True (explicit user consent)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from ..translation.types import TranslationResult
from .models import TranslationRecord


class HistoryRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def record(self, result: TranslationResult, *, store_text: bool = False, source_text: str | None = None) -> str:
        record = TranslationRecord(
            id=str(uuid.uuid4()),
            source_language=result.source_language,
            target_language=result.target_language,
            model_ids=",".join(leg.model_id for leg in result.legs),
            pivot_via=result.pivot_via,
            input_chars=result.input_chars,
            output_chars=result.output_chars,
            segments=result.segments,
            total_ms=result.timings_ms.get("total_ms", 0.0),
            warnings=",".join(w.code for w in result.warnings) or None,
            text_stored=store_text,
            source_text=source_text if store_text else None,
            output_text=result.translation if store_text else None,
        )
        with self._sessions.begin() as session:
            session.add(record)
        return record.id

    def recent(self, limit: int = 50) -> Sequence[TranslationRecord]:
        with self._sessions() as session:
            return session.scalars(select(TranslationRecord).order_by(TranslationRecord.created_at.desc()).limit(limit)).all()

    def count(self) -> int:
        with self._sessions() as session:
            return int(session.scalar(select(func.count()).select_from(TranslationRecord)) or 0)

    def delete_all(self) -> int:
        with self._sessions.begin() as session:
            return session.execute(delete(TranslationRecord)).rowcount or 0

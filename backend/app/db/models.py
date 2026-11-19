"""Tables. Privacy by design: the text columns exist but stay NULL unless the user explicitly opts in per request."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _now() -> datetime:
    return datetime.now(UTC)


class TranslationRecord(Base):
    __tablename__ = "translation_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    source_language: Mapped[str] = mapped_column(String(8))
    target_language: Mapped[str] = mapped_column(String(8))
    model_ids: Mapped[str] = mapped_column(String(200))  # comma-separated; two entries for a pivot
    pivot_via: Mapped[str | None] = mapped_column(String(8), nullable=True)
    input_chars: Mapped[int] = mapped_column(Integer)
    output_chars: Mapped[int] = mapped_column(Integer)
    segments: Mapped[int] = mapped_column(Integer)
    total_ms: Mapped[float] = mapped_column(Float)
    warnings: Mapped[str | None] = mapped_column(String(200), nullable=True)  # comma-separated warning codes
    text_stored: Mapped[bool] = mapped_column(Boolean, default=False)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)

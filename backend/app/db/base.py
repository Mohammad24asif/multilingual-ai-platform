"""SQLAlchemy declarative base. STATUS: not executed in the build sandbox (SQLAlchemy is not installed there)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

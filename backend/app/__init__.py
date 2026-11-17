"""Multilingual AI Intelligence Platform - backend package."""

import logging as _logging

__version__ = "0.1.0"

# Library best practice: stay silent until the application configures logging (core/logging.py),
# so nothing is ever printed with Python's default (message-revealing) format.
_logging.getLogger(__name__).addHandler(_logging.NullHandler())

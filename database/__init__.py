"""Database scripts (SRS submission section 2).

Implementation: ``webapp/services/database.py`` (SQLite schema + access layer for
users, events, alerts, reviews, audit_log). Re-exported here so the database
code + schema are discoverable under the SRS-required folder name.

The schema SQL is available as ``SCHEMA`` for review; see ``schema.sql`` in this
folder for a standalone copy.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "webapp"))

from services.database import SCHEMA, Database  # noqa: E402,F401

__all__ = ["Database", "SCHEMA"]

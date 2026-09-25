"""SQLite database layer for SonicSentinel (SRS: Database Storage lxxii, Audit lxxvi).

Uses the Python standard-library ``sqlite3`` (no heavy ORM dependency). Stores
users, audio events, per-model predictions, alerts, reviews, and an audit trail.
Passwords are hashed with werkzeug's PBKDF2.

The database path comes from config (paths.database, under output_root).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL,
    department    TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id                TEXT PRIMARY KEY,     -- Audio ID / event id
    filename          TEXT,
    stored_path       TEXT,
    uploaded_by       TEXT,
    source_mode       TEXT,                 -- upload | batch | live
    duration          REAL,
    sample_rate       INTEGER,
    channels          INTEGER,
    file_size         INTEGER,
    sha256            TEXT,
    -- python model
    py_class          TEXT,
    py_confidence     REAL,
    py_scores_json    TEXT,
    -- gtm model
    gtm_class         TEXT,
    gtm_confidence    REAL,
    gtm_scores_json   TEXT,
    -- comparison / decision
    agreement         TEXT,                 -- Acceptable Match | Weak Match | Model Disagreement | Uncertain Result
    conf_difference   REAL,
    top_two_margin    REAL,
    audio_quality     TEXT,                 -- Good | Acceptable | Poor | Unusable
    final_class       TEXT,
    severity          TEXT,
    alert_status      TEXT,                 -- None | Active | Acknowledged | Dismissed | Escalated
    manual_review     INTEGER DEFAULT 0,
    status            TEXT,                 -- Uploaded | Classified | Uncertain | Alert Generated | Manual Review | Reviewed | Closed
    waveform_path     TEXT,
    spectrogram_path  TEXT,
    model_versions    TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id           TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL,
    severity     TEXT,
    category     TEXT,
    status       TEXT,                      -- Active | Acknowledged | Dismissed | Escalated
    message      TEXT,
    acted_by     TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id            TEXT PRIMARY KEY,
    event_id      TEXT NOT NULL,
    reviewer      TEXT,
    decision      TEXT,                     -- Confirmed | Corrected | Overridden
    corrected_class TEXT,
    comment       TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor      TEXT,
    action     TEXT,
    detail     TEXT,
    created_at TEXT NOT NULL
);
"""

# Seed accounts (created only if the users table is empty).
SEED_USERS = [
    ("Admin Controller", "admin@sonicsentinel.ai", "admin", "administrator", "Operations"),
    ("Field Operator", "operator@sonicsentinel.ai", "operator", "security_operator", "Security"),
    ("Audio Reviewer", "reviewer@sonicsentinel.ai", "reviewer", "audio_reviewer", "Analysis"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class Database:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self, seed: bool = True) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            if seed:
                count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                if count == 0:
                    for name, email, pwd, role, dept in SEED_USERS:
                        conn.execute(
                            "INSERT INTO users (id, name, email, password_hash, role, department, created_at)"
                            " VALUES (?,?,?,?,?,?,?)",
                            (_new_id("SS-USR"), name, email,
                             generate_password_hash(pwd), role, dept, _now()),
                        )

    # -- users ------------------------------------------------------------
    def create_user(self, name, email, password, role, department) -> dict[str, Any] | None:
        try:
            with self._connect() as conn:
                uid = _new_id("SS-USR")
                conn.execute(
                    "INSERT INTO users (id, name, email, password_hash, role, department, created_at)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (uid, name, email, generate_password_hash(password), role, department, _now()),
                )
            return self.get_user_by_email(email)
        except sqlite3.IntegrityError:
            return None  # email already exists

    def get_user_by_email(self, email) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return dict(row) if row else None

    def verify_login(self, email, password) -> dict[str, Any] | None:
        user = self.get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            return user
        return None

    def update_user(self, email, name=None, department=None) -> None:
        with self._connect() as conn:
            if name is not None:
                conn.execute("UPDATE users SET name = ? WHERE email = ?", (name, email))
            if department is not None:
                conn.execute("UPDATE users SET department = ? WHERE email = ?", (department, email))

    # -- events -----------------------------------------------------------
    def insert_event(self, event: dict[str, Any]) -> str:
        event = dict(event)
        event.setdefault("id", _new_id("EVT"))
        event.setdefault("created_at", _now())
        for key in ("py_scores_json", "gtm_scores_json", "model_versions"):
            if key in event and not isinstance(event[key], str):
                event[key] = json.dumps(event[key])
        cols = ", ".join(event.keys())
        placeholders = ", ".join("?" for _ in event)
        with self._connect() as conn:
            conn.execute(f"INSERT INTO events ({cols}) VALUES ({placeholders})", tuple(event.values()))
        return event["id"]

    def get_event(self, event_id) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            return dict(row) if row else None

    def list_events(self, limit=200, where=None, params=()) -> list[dict[str, Any]]:
        query = "SELECT * FROM events"
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY created_at DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(query, (*params, limit)).fetchall()
            return [dict(r) for r in rows]

    def update_event(self, event_id, **fields) -> None:
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self._connect() as conn:
            conn.execute(f"UPDATE events SET {sets} WHERE id = ?", (*fields.values(), event_id))

    # -- alerts -----------------------------------------------------------
    def insert_alert(self, event_id, severity, category, message, status="Active") -> str:
        aid = _new_id("ALT")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO alerts (id, event_id, severity, category, status, message, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (aid, event_id, severity, category, status, message, _now()),
            )
        return aid

    def list_alerts(self, status=None, limit=200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM alerts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def update_alert(self, alert_id, status, acted_by=None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET status = ?, acted_by = ?, updated_at = ? WHERE id = ?",
                (status, acted_by, _now(), alert_id))

    # -- reviews ----------------------------------------------------------
    def insert_review(self, event_id, reviewer, decision, corrected_class=None, comment=None) -> str:
        rid = _new_id("REV")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO reviews (id, event_id, reviewer, decision, corrected_class, comment, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (rid, event_id, reviewer, decision, corrected_class, comment, _now()))
        return rid

    # -- audit ------------------------------------------------------------
    def audit(self, actor, action, detail="") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (actor, action, detail, created_at) VALUES (?,?,?,?)",
                (actor, action, detail, _now()))

    def list_audit(self, limit=200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    # -- analytics --------------------------------------------------------
    def category_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT final_class, COUNT(*) c FROM events GROUP BY final_class").fetchall()
            return {r["final_class"]: r["c"] for r in rows if r["final_class"]}

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            critical = conn.execute(
                "SELECT COUNT(*) FROM events WHERE severity = 'Critical'").fetchone()[0]
            disagreements = conn.execute(
                "SELECT COUNT(*) FROM events WHERE agreement = 'Model Disagreement'").fetchone()[0]
            poor = conn.execute(
                "SELECT COUNT(*) FROM events WHERE audio_quality IN ('Poor','Unusable')").fetchone()[0]
            avg_conf = conn.execute(
                "SELECT AVG(py_confidence) FROM events").fetchone()[0] or 0.0
            reviews = conn.execute(
                "SELECT COUNT(*) FROM events WHERE manual_review = 1").fetchone()[0]
        return {
            "total_events": total,
            "critical_events": critical,
            "model_disagreements": disagreements,
            "poor_quality": poor,
            "avg_confidence": round(avg_conf, 1),
            "manual_reviews": reviews,
        }

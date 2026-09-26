-- SonicSentinel AI database schema (generated from webapp/services/database.py)

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

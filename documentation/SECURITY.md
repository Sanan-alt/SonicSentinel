# Security & Privacy

## Authentication
- Passwords are hashed with Werkzeug PBKDF2 (`generate_password_hash`); no
  plaintext passwords are stored (`webapp/services/database.py`).
- Login verification is constant-time via `check_password_hash`.

## Secrets
- The Flask session secret comes from `SONICSENTINEL_SECRET_KEY` (environment).
  No secret is hardcoded in source. See `.env.example`.
- A random per-process key is used only for local dev if the env var is unset;
  set the env var in production so sessions survive restarts.
- `.env` is git-ignored.

## Authorization (RBAC)
- Five roles: Normal user, Audio reviewer, Security operator, Maintenance
  operator, Administrator.
- Route access is enforced by the `role_required` decorator in `webapp/app.py`.
  Admin implicitly satisfies any role check.

## Input & file safety
- Uploads are validated for extension, size (≤25 MB), and duration
  (`webapp/services/audio_io.py`). Unsupported/oversized/empty files are rejected.
- Filenames are sanitised with `werkzeug.utils.secure_filename` and stored under
  a content-hash prefix, preventing path traversal and collisions.
- Audio is decoded and integrity-checked before analysis; silent/corrupt clips
  are rejected rather than silently processed.

## Database safety
- All SQL uses parameterised queries (no string interpolation of user input).
- Foreign keys enabled; an append-only `audit_log` records auth, classification,
  review, alert, and admin actions.

## Privacy
- Live microphone audio is captured in short windows; only confirmed critical
  events are persisted. Unconfirmed windows are deleted.
- Reviewer overrides and identities are audited.
- No audio or user data is sent to third-party services. The final
  classification is produced by the local Python model and (when configured) the
  local/browser Google Teachable Machine model — not by any generative-AI API.

## Logging hygiene
- Passwords and secret keys are never logged.
- The audit log stores actor email, action, and a short detail string only.

## Remaining hardening for production
- Serve behind HTTPS (TLS termination via reverse proxy / platform).
- Set `SESSION_COOKIE_SECURE=1` and `SESSION_COOKIE_HTTPONLY=1` behind HTTPS.
- Configure a data-retention/deletion policy for stored uploads and events.
- Rate-limit auth endpoints.

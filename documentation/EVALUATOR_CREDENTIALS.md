# Evaluator & Administrator Credentials (SRS sections 11, 12)

These demo accounts are created automatically on first run (the users table is
seeded only when empty — see `webapp/services/database.py`). They are for local
evaluation of a prototype; change them before any real deployment.

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@sonicsentinel.ai` | `admin` |
| Security Operator | `operator@sonicsentinel.ai` | `operator` |
| Audio Reviewer | `reviewer@sonicsentinel.ai` | `reviewer` |

## Notes
- Passwords are stored **hashed** (PBKDF2); the table above is the seed plaintext
  for evaluation convenience only.
- New users can self-register via `/register` and pick a role.
- For a public deployment, set a real `SONICSENTINEL_SECRET_KEY` (see `.env.example`)
  and rotate/replace these demo accounts.

## Where to enter them
- Local: run `python webapp/app.py`, open http://localhost:5000, click a demo
  button on the login page or type the credentials above.

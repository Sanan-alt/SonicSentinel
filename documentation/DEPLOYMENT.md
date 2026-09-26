# Deployment (SRS section 12)

> No public deployment URL is claimed. This document provides complete local +
> container deployment so an evaluator can run the system. A URL will be added
> here only if/when a real deployment exists.

## Local (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# provide raw audio under Dataset/, then:
python src/run_pipeline.py            # organize -> features -> train
$env:SONICSENTINEL_SECRET_KEY = python -c "import secrets;print(secrets.token_hex(32))"
python webapp/app.py                  # http://localhost:5000
```

## Local (macOS/Linux)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/run_pipeline.py
export SONICSENTINEL_SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
python webapp/app.py
```

## Docker
```bash
docker compose build
SONICSENTINEL_SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))") \
  docker compose up
```
For containers, set `paths.output_root` in `config/config.yaml` to `/data`
(the mounted volume) so generated artefacts persist and are writable.

## Production considerations
- Serve behind HTTPS (reverse proxy / platform TLS). Set secure session cookies.
- Use a WSGI server (`gunicorn`) instead of the Flask dev server on Linux.
- Provide a trained Python model (`models/python/`) and, if available, a GTM
  export (`models/gtm/export/`).
- Set `SONICSENTINEL_SECRET_KEY` and rotate the demo accounts.
- Configure data retention/deletion for uploads and events.

## Environment variables
See `.env.example`: `SONICSENTINEL_SECRET_KEY`, `SONIC_BG_TRAIN`,
`SONIC_TRAIN_INTERVAL`, `SONIC_N_JOBS`.

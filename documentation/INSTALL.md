# Installation & Execution Guide — SonicSentinel AI

## Prerequisites
- **OS:** Windows / macOS / Linux
- **Python:** 3.11–3.13
- **RAM:** 8 GB+ recommended
- **Disk:** ~2 GB free for dependencies + generated artefacts

## 1. Get the code
```powershell
git clone https://github.com/Sanan-alt/SonicSentinel.git
cd SonicSentinel
```

## 2. Virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
```

## 3. Install dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
> MP3/M4A decoding is handled by `soundfile` + `audioread`. If a format fails to
> decode on your system, install **FFmpeg** and add it to `PATH`.

## 4. Configure storage (important)
Generated data (dataset copies, features, models, uploads, database) is written
under `paths.output_root` in `config/config.yaml`. Set it to any location with
free space:
```yaml
paths:
  output_root: "D:/sonicsentinel_data"   # change as needed
```

## 5. Add audio data
Place raw audio under `Dataset/`:
- ESC-50 `.wav` clips in `Dataset/Dataset/audio/`
- Your hand-collected category folders (e.g. mp3) referenced in `config.yaml`.

## 6. Build the models
```powershell
python src/run_pipeline.py        # organize -> features -> train (one command)
# or step by step:
python src/organize.py            # dedup + label + 70/15/15 stratified split + metadata
python src/extract_features.py    # acoustic features (+ train-only augmentation)
python src/train.py               # best Python model + 2nd comparison model + reports
python src/build_dataset_docs.py  # data/metadata + data/splits deliverables
python src/validate_dataset.py    # dataset quality/integrity report
python src/compare_models.py      # model comparison report (unseen test set)
python src/generate_reports.py    # mirror evidence into reports/ + model_metadata.json
```
Artefacts land under `output_root`:
- `python_models/sonicsentinel_model.joblib` (best Python model + preprocessing pipeline)
- `python_models/python2/second_model.joblib` (second model for comparison)
- `reports/metrics.json`, `confusion_matrix.png`, `model_comparison_report.csv`

### Python model placement
The web app loads the model from `paths.models_dir` under `output_root`
(default `D:/sonicsentinel_data/python_models/`). If you receive a pre-trained
model, drop `sonicsentinel_model.joblib` there.

### Google Teachable Machine placement (real GTM)
GTM is browser-only. After creating/exporting it (see
`documentation/GOOGLE_TEACHABLE_MACHINE.md`), place the export in
`models/gtm/export/` (repo) — the app validates and loads it. Until then the app
shows GTM = "Not available" and marks the comparison BLOCKED (never faked).

## 7. Environment variables
Copy `.env.example` to `.env` (git-ignored) or set in your shell:
```powershell
$env:SONICSENTINEL_SECRET_KEY = python -c "import secrets;print(secrets.token_hex(32))"
$env:SONIC_BG_TRAIN = "1"          # background retraining on (0 to disable)
$env:SONIC_N_JOBS = "1"            # training parallelism (1 = safest / low RAM)
```

## 8. Database configuration & initialization
- SQLite is used; the DB file path is `paths.database` under `output_root`.
- The schema is created and demo users are seeded **automatically on first run**
  (`db.init_db(seed=True)` in `webapp/app.py`). No manual migration is needed.
- Standalone schema for review: `database/schema.sql`.

## 9. Run the web app
```powershell
python webapp/app.py
```
Open http://localhost:5000. The SQLite database is created and seeded on first run.

**Demo accounts:** `admin@sonicsentinel.ai / admin`,
`operator@sonicsentinel.ai / operator`, `reviewer@sonicsentinel.ai / reviewer`
(see `documentation/EVALUATOR_CREDENTIALS.md`).

## 10. Run tests
```powershell
python -m pytest -q                 # unit + functional + SRS cases
python scripts/run_all_tests.py     # env + dataset + pytest + SRS audit (writes reports/final/)
python scripts/final_srs_audit.py   # evidence-driven compliance report
```

## Troubleshooting
| Problem | Fix |
|---|---|
| `Model unavailable` in the UI | Run `python src/train.py` first. |
| MP3/M4A won't decode | Install FFmpeg and add to PATH. |
| `No space left on device` | Point `output_root` at a drive with free space. |
| Mic not working in Live Monitor | Allow microphone permission in the browser. |
| GTM shows "Not available" | Expected until you add a browser export to `models/gtm/export/`. |
| Sessions reset on restart | Set `SONICSENTINEL_SECRET_KEY` (otherwise a random dev key is used). |
| Training crashes / out of memory | Set `SONIC_N_JOBS=1` and lower `augmentation.per_clip` / `features.n_fft` in config. |

## Administrator / configuration
- **Alert rules:** edit `alert_rules/alert_rules.json` (or Admin → Settings at runtime).
- **Audio/feature settings:** edit `config/config.yaml`.
- **Add a sound class / data:** drop audio into `Dataset/<folder>/`, add the mapping
  in `config.yaml` + `src/sonic/labels.py`, then re-run step 6. The background
  trainer also picks up new data automatically while the app runs.
- **Admin setup:** log in as `admin@sonicsentinel.ai`; use Admin → Settings to tune
  thresholds and `/api/trainer-run` to trigger a retrain.
